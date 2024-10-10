import pytest
from src import openai

def test_num_tokens_from_string():
    test_string = "Hello, world!"
    assert openai.num_tokens_from_string(test_string) == 4

def test_get_tokens_from_string():
    test_string = "Hello, world!"
    assert openai.get_tokens_from_string(test_string) == [9906, 11, 1917, 0]

def test_get_string_from_tokens():
    tokens = [9906, 11, 1917, 0]  # Adjust based on your tokenizer
    expected_string = "Hello, world!"
    assert openai.get_string_from_tokens(tokens) == expected_string

def test_check_token_limit():
    test_string = "Hello, world!"*5000
    openai.TOKEN_LIMIT = 5  # Set a limit for testing
    with pytest.raises(ValueError):
        openai.check_token_limit(test_string)

def test_get_embedding():

    test_string = "Hello, world!"
    embeddings = openai.get_embedding(test_string)
    assert isinstance(embeddings, list)
    assert len(embeddings) == 1536