import os
from openai import OpenAI
import tiktoken
import time

from src import db

ENCODER = os.getenv("OPENAI_ENCODER")
EMBEDDING_MODEL_NAME = os.getenv("OPENAI_EMBEDDING_MODEL")
TOKEN_LIMIT = int(os.getenv("OPENAI_EMBEDDING_MODEL_TOKEN_LIMIT"))

system_prompt = """
You are an intelligent assistant that answers questions based on provided
domain knowledge. Be brief in your answers.

Your domain knowledge comes from a specific forum where users ask questions and receive answers.

Use ONLY the provided context information to form your response.

If there isn't enough information below, say you don't know. Do not generate
answers that don't use the sources below.

If asking a clarifying question to the user would help, ask the question.

Each source contains information about a specific post. Each source has a title
and a body. Always include the source ID for each fact you use in the response.

Use double square brackets to reference the source, for example [[info1.txt]].
Don't combine sources, list each source separately, for example [[info1.txt]][[info2.pdf]]
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

        with open("prompt.txt", "w") as f:
            f.write(prompt)

        # Check prompt token limit
        n_tokens = get_num_tokens_from_string(prompt)
        if n_tokens > 100_000:
            raise ValueError(f"Prompt is too big. Number of tokens is {n_tokens}.")

        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"{system_prompt}\n{follow_up_questions_prompt}",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        import json

        with open("response.json", "w") as f:
            f.write(json.dumps(completion.to_dict(), indent=4))

        response = completion.choices[0].message.content

        response = response.replace("[[info1.txt]]", '""')
        response = response.replace("[[info2.pdf]]", '""')
        return response
