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
                'score': 10,
                'created': 1620000000,
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
        assert len(posts) == len(5)



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
