from src import db


def test_insert_reddit_post():

    try:
        db.insert_reddit_post(
            {
                "id": "11AAZZ",
                "title": "What do you think about this?",
                "selftext": "This is a test post",
                "ups": 10,
                "downs": 2,
                "link_flair_text": "test",
                "num_comments": 14,
                "permalink": "test",
                "score": 10,
                "created": 1620000000,
            }
        )

        with db.Session(db.engine) as session:
            post = session.query(db.RedditPosts).filter_by(id="11AAZZ").first()
            assert post.title == "What do you think about this?"
            assert post.description == "This is a test post"
            assert post.upvotes == 10
            assert post.downvotes == 2
            assert post.tag == "test"
            assert post.num_comments == 14
            assert post.permalink == "test"
            assert len(post.content_hash) == 32
    except Exception as e:
        raise e
    finally:
        with db.Session(db.engine) as session:
            session.query(db.RedditPosts).filter_by(id="11AAZZ").delete()
            session.commit()


def test_get_posts_url():
    urls = db.get_posts_url(["1cx4mbl", "1dxpqvk"])
    assert type(urls) == dict
    assert len(urls) > 0
    assert urls == {
        "1cx4mbl": "/r/dataengineering/comments/1cx4mbl/do_you_guys_think_he_has_a_point/",
        "1dxpqvk": "/r/dataengineering/comments/1dxpqvk/sales_of_vibrators_spike_every_august/",
    }

    # checks urls are returned in alphabetical order
    urls = db.get_posts_url(["1dxpqvk", "1cx4mbl"])
    assert type(urls) == dict
    assert len(urls) > 0
    assert urls == {
        "1cx4mbl": "/r/dataengineering/comments/1cx4mbl/do_you_guys_think_he_has_a_point/",
        "1dxpqvk": "/r/dataengineering/comments/1dxpqvk/sales_of_vibrators_spike_every_august/",
    }


def test_vector_search():

    rows = db.vector_search(
        "what are key features of a good data engineering team?", limit=5
    )
    assert type(rows) == list
    assert len(rows[0]) == 2
    assert type(rows[0][1]) == int
    ids = [r[0] for r in rows]

    with db.Session(db.engine) as session:
        posts = session.query(db.Documents).filter(db.Documents.id.in_(ids)).all()
        assert len(posts) == 5


def test_keyword_search():

    rows = db.keyword_search("What are key features of a snowflake", limit=5)
    assert type(rows) == list
    assert len(rows[0]) == 2
    assert type(rows[0][1]) == int


def test_keyword_search_match_all():
    query = "What are key features of argentina with snowflake"

    rows = db.keyword_search(query, limit=5)
    assert type(rows) == list
    assert len(rows[0]) == 2
    assert type(rows[0][1]) == int

    # DEV NOTE: This test is expected to fail because the query is too specific
    rows = db.keyword_search_match_all(query, limit=5)
    assert len(rows) == 0


def test_hybrid_search():

    rows = db.hybrid_search("What are key features of a snowflake Argentina", limit=5)

    assert type(rows) == list
    assert len(rows) == 5  # 5 rows
    assert len(rows[0]) == 4  # 4 columns

    # check id attribute
    assert type(rows[0][0]) == str
    assert "_" in rows[0][0]

    # check title and score attributes
    assert type(rows[0][1]) == str
    assert float(rows[0][2]) > 0

    # check content attribute
    assert type(rows[0][3]) == str
    assert len(rows[0][3]) > 100


def test_is_post_modified():
    result = db.is_post_modified("1fwv29o")
    assert result == True


def test_get_posts_without_documents():
    result = db.get_posts_without_documents()
    assert len(result) == 0
