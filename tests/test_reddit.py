import json

from src import reddit


def test_get_auth_token():

    token = reddit.get_auth_token()
    assert isinstance(token, str)
    assert len(token) > 0


def test_get_top_posts():

    posts = reddit.get_top_posts("dataengineering", limit=5, t="day")
    assert isinstance(posts, list)
    assert len(posts) == 5
    assert all(isinstance(post, dict) for post in posts)

    post = posts[0]
    assert "name" in post
    assert "title" in post
    assert "author" in post
    assert "selftext" in post


def test_get_all_comments_in_post():

    # Get sample post
    posts = reddit.get_top_posts("dataengineering", limit=1, t="day")
    assert isinstance(posts, list)
    post = posts[0]
    post_id = post["id"]
    comments = reddit.get_all_comments_in_post(post_id)
    assert isinstance(comments, str)
