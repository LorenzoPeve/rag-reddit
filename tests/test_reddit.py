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


def test_get_post_from_url():

    url = "/r/dataengineering/comments/1fs80oq/my_job_hunt_journey_for_remote_data_engineering/"
    post = reddit.get_post_from_url(url)


def test_get_post_from_id():

    r = reddit.get_post_from_id("1fs80oq")
    assert r['num_comments'] > 100
    assert r['upvotes'] > 500
    assert "Europe" in r['title']


def test_get_all_comments_in_post():

    # Get sample post
    posts = reddit.get_top_posts("dataengineering", limit=1, t="day")
    assert isinstance(posts, list)
    post = posts[0]
    post_id = post["id"]
    comments = reddit.get_all_comments_in_post(post_id)
    assert isinstance(comments, str)


def test_posts_and_comments():

    posts = reddit.get_top_posts("dataengineering", limit=15, t="month")

    out = []
    for post in posts:
        comments = reddit.get_all_comments_in_post(post["id"])
        assert isinstance(comments, str)
        assert len(comments) > 0
        out.append({"post": post["permalink"], "comments": comments})

    with open("posts_and_comments2.json", "w") as f:
        json.dump(out, f, indent=4)
