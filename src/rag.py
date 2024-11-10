import os
from openai import OpenAI
import tiktoken
import time

from src import db

ENCODER = os.getenv("OPENAI_ENCODER")
EMBEDDING_MODEL_NAME = os.getenv("OPENAI_EMBEDDING_MODEL")
TOKEN_LIMIT = int(os.getenv("OPENAI_EMBEDDING_MODEL_TOKEN_LIMIT"))

system_prompt = """
You are an intelligent assistant that provides accurate, well-structured responses based on the provided context from a knowledge base of forum posts. Follow these guidelines precisely:

RESPONSE STRUCTURE:
1. Begin with a clear, direct answer to the question. Be brief.
2. Support each point with evidence from the provided context
3. End with a "Citations:" section listing all referenced sources
4. Each unique piece of information should be cited only ONCE using its first mention
5. After Citations, add a "Follow-up Questions:" section with 3 relevant questions

CITATION RULES:
- Use numbered citations in square brackets [1] within your response
- Under "Citations:", list each source exactly ONCE using the format: [1] "Post Title"
- When multiple pieces of information come from the same source, use the same citation number
- DO NOT repeat citations for the same information within the response
- Place citations immediately after the specific information they support, not at the end of sentences containing multiple facts

CONTENT GUIDELINES:
- Use ONLY information from the provided context
- If the context is insufficient, state: "I don't have enough information to fully answer this question."
- If multiple sources conflict, acknowledge the contradiction and cite both sources
- Maintain objectivity by presenting information as stated in the sources
- Preserve the original meaning without embellishment

FOLLOW-UP QUESTIONS RULES:
- Generate 3 brief, relevant follow-up questions based on the context and initial answer
- Each question should be enclosed in double angle brackets
- Questions should explore different aspects of the topic
- Do not repeat the original question
- Questions should be natural extensions of the conversation

Example Response Format:
[Your answer with citations]

Citations:
[1] "Post Title 1"
[2] "Post Title 2"

Follow-up Questions:
<<How does this compare to alternative approaches?>>
<<What are the cost implications of this solution?>>
<<Are there any specific requirements for implementation?>>

INTERACTION GUIDELINES:
- If clarification would help, ask ONE specific question related to the query
- If technical terms appear in the context, explain them using only provided information
- Keep responses concise while including all relevant information
- Match the technical level of the response to the user's question

INCORRECT CITATION EXAMPLE:
❌ "Azure integrates well with Microsoft products [1]. It works especially well with Office 365 [1] and provides good Windows Server support [1]."

CORRECT CITATION EXAMPLE:
✓ "Azure integrates well with Microsoft products, including Office 365 and Windows Server [1]."

FORMAT EXAMPLE:
User Question: "What are the benefits of X?"

Response:
X offers improved efficiency through automated processes and reduces operational costs by 25% [1]. Additionally, it provides enhanced security features [2].

Citations:
[1] "Understanding X Benefits"
[2] "Security Analysis of X"

Follow-up Questions:
<<How does this compare to alternative approaches?>>
<<What are the cost implications of this solution?>>
<<Are there any specific requirements for implementation?>>

RESTRICTIONS:
- Do not make assumptions beyond the provided context
- Do not combine information from different sources without clear citation
- Do not provide personal opinions or recommendations
- Do not reference external knowledge or sources
- Do not repeat citations unnecessarily

ERROR HANDLING:
- If you detect ambiguity in the question, seek clarification before answering
- If the context contains outdated information, note the date from the source
- If information appears contradictory, present both perspectives with citations

Example of expected output for comparison:
Q: "What is the difference between AWS and Azure?"

Azure has stronger integration with Microsoft products, including Office 365 and Windows Server [1]. AWS, as the cloud market pioneer, provides a wider range of services with more customization options [1].

Citations:
[1] "Is Azure best than AWS?"
""".strip()

follow_up_questions_prompt = """
Generate 3 very brief follow-up questions that the user would likely ask next.
Enclose the follow-up questions in double angle brackets. Example:
<<Are there exclusions for prescriptions?>>
<<Which pharmacies can be ordered from?>>
<<What is the limit for over-the-counter medication?>>
Do no repeat questions that have already been asked.
Make sure the last question ends with ">>".
""".strip()


def get_num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(ENCODER)
    return len(encoding.encode(string))


def get_tokens_from_string(string: str) -> list[int]:
    return tiktoken.get_encoding(ENCODER).encode(string)


def get_string_from_tokens(tokens: list[int]) -> str:
    return tiktoken.get_encoding(ENCODER).decode(tokens)


def check_token_limit(string: str) -> int:
    """
    Raise an error if the input string exceeds the token limit for the
    embedding model.
    """
    num_tokens = num_tokens = get_num_tokens_from_string(string)
    if num_tokens > TOKEN_LIMIT:
        raise ValueError(
            f"Input text exceeds token limit of {TOKEN_LIMIT}. Found {num_tokens} tokens."
        )


class ThrottledOpenAI:
    """Class that wraps the OpenAI client to avoid rate limiting errors."""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._remaining_requests = None

    def get_embedding(self, string: str) -> list[float]:
        """Get the embedding for a string using the specified OpenAI client."""
        response = self.client.embeddings.with_raw_response.create(
            model=EMBEDDING_MODEL_NAME, input=string
        )

        if response.status_code == 200:
            x = response.headers.get('x-ratelimit-remaining-requests')
            # caveman rate limiting
            if int(x) > 50:
                time.sleep(5)

            return response.parse().data[0].embedding
        else:
            raise ValueError(f"Error getting embedding: {response.errors}")

    def rag_query(self, question: str) -> str:
        sources: list[tuple] = db.hybrid_search(question, limit=5)

        # Recall output from db.hybrid_search is in the form (id, title, score, content)
        parsed_sources = []
        for source in sources:
            post_id = source[0]
            title = source[1]
            body = source[3]

            if body.startswith(title):
                body = body[len(title) :].strip()

            parsed_sources.append((post_id, title, body))

        # Generate prompt with context
        prompt = (
            f"Based on the following context, answer the user's question.\n"
            f"Question: {question}\n\n"
            f"Context:\n\n"
        )

        for post_id, title, body in parsed_sources:
            prompt += f"Post ID: {post_id}\nTitle: {title}\nBody: {body}\n\n"
       
        with open("prompt.txt", "w", encoding='utf-8') as f:
            f.write(prompt)

        # Check prompt token limit
        n_tokens = get_num_tokens_from_string(prompt)
        if n_tokens > 100_000:
            raise ValueError(f"Prompt is too big. Number of tokens is {n_tokens}.")

        stream = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": f"{system_prompt}\n{follow_up_questions_prompt}",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            stream=True  # Enable streaming
        )

        # Stream the response chunks
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
