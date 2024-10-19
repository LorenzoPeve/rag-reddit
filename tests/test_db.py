from src import db


def test_insert_reddit_post():

    db.init_schema()
    db.insert_reddit_post(
        {
            "id": "1fs80oq",
            "title": "What do you think about this?",
            "selftext": "This is a test post",
            "ups": 10,
            "downs": 2,
            "link_flair_text": "test",
            "num_comments": 14,
            "permalink": "test",
        }
    )

    with db.Session(db.get_db_engine()) as session:
        post = session.query(db.RedditPosts).filter_by(id="1fs80oq").first()
        assert post.title == "What do you think about this?"
        assert post.description == "This is a test post"
        assert post.upvotes == 10
        assert post.downvotes == 2
        assert post.tag == "test"
        assert post.num_comments == 14
        assert post.permalink == "test"
        assert len(post.content_hash) == 32


def test_vector_search():

    rows = db.vector_search(
        "what are key features of a good data engineering team?", limit=5
    )
    assert type(rows) == list
    assert len(rows[0]) == 2
    assert type(rows[0][1]) == int


def test_keywork_search():

    rows = db.keyword_search("What are key features of a snowflake", limit=5)
    assert type(rows) == list
    assert len(rows[0]) == 2
    assert type(rows[0][1]) == int


def test_hybrid_search():

    rows = db.hybrid_search("What are key features of a snowflake", limit=5)
    assert type(rows) == list
    assert len(rows[0]) == 4
    assert type(rows[0][0]) == str
    assert "_" in rows[0][0]
    assert type(rows[0][1]) == str
    assert float(rows[0][2]) > 0
    assert type(rows[0][3]) == str
    assert len(rows[0][3]) > 100


def test_is_post_modified():
    result = db.is_post_modified("1fwv29o")
    assert result == True


def test_get_posts_without_documents():
    result = db.get_posts_without_documents()
    assert len(result) == 0
