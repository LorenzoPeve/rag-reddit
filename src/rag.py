import os
from openai import OpenAI
import tiktoken
import time

from src import db

ENCODER = os.getenv("OPENAI_ENCODER")
EMBEDDING_MODEL_NAME = os.getenv("OPENAI_EMBEDDING_MODEL")
TOKEN_LIMIT = int(os.getenv("OPENAI_EMBEDDING_MODEL_TOKEN_LIMIT"))

system_prompt = """
You are an intelligent assistant that provides accurate, well-structured responses based on the provided context from forum posts. Follow these guidelines precisely:

RESPONSE STRUCTURE:
1. Begin with a clear, direct answer to the question. Be brief.
2. Support each point with evidence from the provided context
3. End with a "Citations:" section listing all referenced sources
4. After Citations, add a "Follow-up Questions:" section with 3 relevant questions

CITATION RULES:
- Use numbered citations in square brackets [1] within your response
- Under "Citations:", each unique post/thread should have exactly ONE citation number
- ALL information from the same post/thread MUST use the same citation number, even if discussing different examples
- Format citations as: [1] "Post Title"[[Post ID]]

CRITICAL: SALARY DATA EXAMPLE
❌ INCORRECT WAY:
"One engineer in San Francisco makes $190k [1]. Another in Chicago makes $140k [2]."
Citations:
[1] "Salary Discussion Thread"[[post123]]
[2] "Salary Discussion Thread"[[post123]]

✓ CORRECT WAY:
"The salary data shows various ranges: an engineer in San Francisco makes $190k, while another in Chicago makes $140k [1]."
Citations:
[1] "Salary Discussion Thread"[[post123]]

HANDLING MULTIPLE DATA POINTS:
- When multiple examples, data points, or cases come from the same thread:
  1. Group them together in your response
  2. Use a single citation for all information from that thread
  3. Present them as different examples from the same source
  
Example of grouping data:
"The salary survey revealed multiple cases: a San Francisco-based engineer earning $190k, a Chicago-based engineer making $140k, and a remote worker receiving $165k, showing the wide range of compensation in the field [1]."

CONTENT GUIDELINES:
- Use ONLY information from the provided context
- If the context is insufficient, state: "I don't have enough information to fully answer this question."
- Maintain objectivity by presenting information as stated in the sources
- When presenting multiple examples from the same source, use connecting phrases like:
  * "From the same survey..."
  * "The thread includes multiple examples..."
  * "Various cases reported include..."
  * "Different respondents in the same discussion reported..."

FOLLOW-UP QUESTIONS RULES:
- Generate 3 brief, relevant follow-up questions
- Each question should be enclosed in double angle brackets
- Questions should explore different aspects of the topic

RESTRICTIONS:
- NEVER create separate citation numbers for information from the same post/thread
- ALL examples from the same thread MUST be grouped under ONE citation
- Do not make assumptions beyond the provided context
- Do not provide personal opinions

FORMAT EXAMPLE:
User: "What are current DE salaries?"

Response:
The salary thread shows varied compensation across locations and experience levels: San Francisco-based engineers reported ranges of $190-210k, Chicago-based roles showed $140-160k, and remote positions indicated $165-185k ranges [1]. 

Citations:
[1] "Salary Discussion 2024"[[post123]]

Follow-up Questions:
<<What benefits packages typically accompany these salary ranges?>>
<<How do these salaries compare to other tech roles?>>
<<What skills command the highest compensation?>>
"""

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
        self.usage = 0

    def get_embedding(self, string: str) -> list[float]:
        """Get the embedding for a string using the specified OpenAI client."""
        response = self.client.embeddings.with_raw_response.create(
            model=EMBEDDING_MODEL_NAME, input=string
        )

        total_tokens = response.parse().usage.total_tokens
        print(f"Embedding tokens: {total_tokens}")

        if response.status_code == 200:
            x = response.headers.get("x-ratelimit-remaining-requests")
            # caveman rate limiting
            if int(x) > 50:
                time.sleep(5)

            return response.parse().data[0].embedding
        else:
            raise ValueError(f"Error getting embedding: {response.errors}")

    def rag_query(self, question: str) -> str:

        self.usage = 0
        sources: list[tuple] = db.hybrid_search(question, limit=5)

        # Recall output from db.hybrid_search is in the form (id, title, score, content)
        parsed_sources = []
        for source in sources:
            post_id = source[1]
            title = source[2]
            body = source[4]

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

        with open("prompt.txt", "w", encoding="utf-8") as f:
            f.write(prompt)

        # Check prompt token limit
        n_tokens = get_num_tokens_from_string(prompt)
        if n_tokens > 100_000:
            raise ValueError(f"Prompt is too big. Number of tokens is {n_tokens}.")
        else:
            print(f"Number of tokens in prompt: {n_tokens}")

        stream = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"{system_prompt}\n{follow_up_questions_prompt}",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            stream=True,  # Enable streaming
        )

        # Stream the response chunks
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                self.usage += get_num_tokens_from_string(content)
                yield content
        else:
            print(f"Ouput tokens: {self.usage}")
