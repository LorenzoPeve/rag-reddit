import os
import tiktoken

ENCODER = os.getenv("OPENAI_ENCODER")
MODEL = os.getenv('OPENAI_EMBEDDING_MODEL')
TOKEN_LIMIT = int(os.getenv('OPENAI_EMBEDDING_MODEL_TOKEN_LIMIT'))

def num_tokens_from_string(string: str) -> int:
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
    num_tokens = num_tokens = num_tokens_from_string(string)
    if num_tokens > TOKEN_LIMIT:
        raise ValueError(f"Input text exceeds token limit of {TOKEN_LIMIT}. Found {num_tokens} tokens.")