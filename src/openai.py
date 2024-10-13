import os
from openai import OpenAI
import tiktoken

from src import db

ENCODER = os.getenv("OPENAI_ENCODER")
EMBEDDING_MODEL_NAME = os.getenv("OPENAI_EMBEDDING_MODEL")
TOKEN_LIMIT = int(os.getenv("OPENAI_EMBEDDING_MODEL_TOKEN_LIMIT"))
OPENAI_CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


system_prompt = """
You are an intelligent assistant that answers questions based on provided
domain knowledge. Be brief in your answers.

Your domain knowledge comes from a specific forum where users ask questions and receive answers.

Answer ONLY with the facts listed in the list of sources below.

If there isn't enough information below, say you don't know. Do not generate
answers that don't use the sources below.

If asking a clarifying question to the user would help, ask the question.

If the question is not in English, translate to English and then answer the question.

Each source contains information about a specific post. Each source has a title
and a body.
""".strip()

follow_up_questions_prompt_content = """
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


def get_embedding(string: str) -> list[float]:
    """Get the embedding for a string using the specified OpenAI client."""
    response = OPENAI_CLIENT.embeddings.create(model=EMBEDDING_MODEL_NAME, input=string)

    return response.data[0].embedding


def rag_query(
    question: str,
    sources: list[(tuple[str, str])],
):

    pass
