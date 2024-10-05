import json

from src import reddit

def test_get_auth_token():
    
    token = reddit.get_auth_token()
    assert isinstance(token, str)
    assert len(token) > 0



def test_get_top_posts():

    posts = reddit.get_top_posts('dataengineering', limit=5, t='day')
    assert isinstance(posts, list)
    assert len(posts) == 5
    assert all(isinstance(post, dict) for post in posts)

    post = posts[0]
    assert 'kind' in post
    assert post['kind'] == 't3'
    assert 'data' in post
    assert 'name' in post['data']
    assert 'title' in post['data']
    assert 'author' in post['data']
    assert 'selftext' in post['data']

def test_get_all_comments_in_post():

    # Get sample post
    posts = reddit.get_top_posts('dataengineering', limit=1, t='day')
    assert isinstance(posts, list)
    post = posts[0]
    post_id = post['data']['id']
    comments = reddit.get_all_comments_in_post(post_id)
    assert isinstance(comments, str)
