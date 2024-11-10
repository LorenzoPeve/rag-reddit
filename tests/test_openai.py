import pytest

from src import db, rag


def test_get_num_tokens_from_string():
    test_string = "Hello, world!"
    assert rag.get_num_tokens_from_string(test_string) == 4


def test_get_tokens_from_string():
    test_string = "Hello, world!"
    assert rag.get_tokens_from_string(test_string) == [9906, 11, 1917, 0]


def test_get_string_from_tokens():
    tokens = [9906, 11, 1917, 0]
    expected_string = "Hello, world!"
    assert rag.get_string_from_tokens(tokens) == expected_string


def test_check_token_limit():
    test_string = "Hello, world!" * 5000
    rag.TOKEN_LIMIT = 5
    with pytest.raises(ValueError):
        rag.check_token_limit(test_string)


def test_get_embedding():

    test_string = "Hello, world!"
    client = rag.ThrottledOpenAI()
    embeddings = client.get_embedding(test_string)
    assert isinstance(embeddings, list)
    assert len(embeddings) == 1536


def test_get_embedding_2():

    test_string = "What are key features of a good data engineering team?"
    client = rag.ThrottledOpenAI()
    embeddings = client.get_embedding(test_string)
    assert isinstance(embeddings, list)
    assert len(embeddings) == 1536

def test_rag_query():
    question = "Currently, what is the best API for web scraping large swaths of data?"
    client = rag.ThrottledOpenAI()
    response = client.rag_query(question)
    response_list = list(response)