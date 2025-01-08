import os
import praw
import re
import requests
from requests.auth import HTTPBasicAuth
import unicodedata

from src import db

REDDIT = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("USER_AGENT"),
)


def get_auth_token() -> str:
    """
    Retrieves an authentication token from the Reddit API. If the request is
    successful, it returns the access token. Otherwise, it raises an exception.
    """
    url = "https://www.reddit.com/api/v1/access_token"

    response = requests.post(
        url,
        auth=HTTPBasicAuth(
            os.getenv("REDDIT_CLIENT_ID"), os.getenv("REDDIT_CLIENT_SECRET")
        ),
        data={
            "grant_type": "password",
            "username": os.getenv("REDDIT_USER"),
            "password": os.getenv("REDDIT_USER_PASSWORD"),
        },
        headers={"User-Agent": os.getenv("USER_AGENT")},
    )

    if response.status_code != 200:
        raise Exception(f"Failed to get token. Error: {response.text}")
    return response.json()["access_token"]


def get_top_posts(subreddit: str, limit: int = 100, t: str = "month", after: str = None) -> list[dict]:
    """
    Fetches the top posts from a specified subreddit within a given time frame.
    Args:
        subreddit (str): The name of the subreddit to fetch posts from.
        limit (int, optional): The maximum number of posts to fetch. Defaults to 100.
        t (str, optional): The time frame to fetch top posts for. One of 'hour', 'day', 'week', 'month', 'year', 'all'. Defaults to 'month'.
    Returns:
        dict: A dictionary containing the top posts data.
    Raises:
        Exception: If the request to the Reddit API fails.
    """
    response = requests.get(
        f"https://oauth.reddit.com/r/{subreddit}/top",
        headers={
            "Authorization": f"bearer {get_auth_token()}",
            "User-Agent": os.getenv("USER_AGENT"),
        },
        params={"limit": limit, "t": t, 'after': after},
    )

    if response.status_code != 200:
        raise Exception(
            f"Failed to get top posts from {subreddit}. Error: {response.text}"
        )

    r = response.json()["data"]["children"]

    # Extract the post data from the response for each post
    out = []
    for post in r:
        assert post["kind"] == "t3"
        out.append(post["data"])
    return out


def get_post_from_id(post_id: str) -> dict:
    """Fetches a Reddit post using the post's unique identifier."""
    r = REDDIT.submission(id=post_id)
    return dict(
        id=post_id,
        title=r.title,
        description=r.selftext,
        score=r.score,
        upvotes=r.ups,
        downvotes=r.downs,
        tag=r.link_flair_text,
        num_comments=r.num_comments,
        permalink=r.permalink,
        created=r.created_utc,
    )


def get_post_from_url(url: str) -> dict:
    """
    Fetches a Reddit post using the post's URL. The URL must be in the format:
    /r/{subreddit}/{id}/{title}/
    """
    assert url.startswith("/r/")

    response = requests.get(
        f"https://oauth.reddit.com/{url}",
        headers={
            "Authorization": f"bearer {get_auth_token()}",
            "User-Agent": os.getenv("USER_AGENT"),
        },
    )

    if response.status_code != 200:
        raise Exception(
            f"Failed to get top posts from {response.url}. Error: {response.text}"
        )

    return response.json()


def sanitize_text(text):
    """
    Sanitizes text by removing special characters, html tags, and normalizing
    whitespace.
    """
    text = re.sub(r"\s+", " ", text).strip()  # normalize whitespace
    text = re.sub(r"\n", " ", text).strip()
    text = re.sub(r"<.*?>", "", text)  # remove html tags
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    return text


def traverse_comments(
    comment: praw.models.Comment,
    collected_comments: list,
    depth: int = 0,
    max_depth: int = 4,
):
    """
    Recursively traverses a comment tree and collects the comment bodies into a list up to a specified depth.
        comment (praw.models.Comment): The current Reddit comment object.
        collected_comments (list): A list to collect the comments' body text.
        depth (int): The current depth level of recursion (default is 0).
        max_depth (int): The maximum depth to traverse (default is 4).
    Returns:
        None: The function modifies the collected_comments list in place.
    """
    if depth > max_depth:
        return

    # Skip comments made by the bot
    if "I am a bot, and this action was performed automatically" in comment.body:
        return

    if comment.body.startswith("RemindMe! "):
        return

    discard = [
        "following",
        "following!",
        "+1",
        "[deleted]",
        "deleted",
    ]

    if comment.body.lower() not in discard:
        collected_comments.append(sanitize_text(comment.body))

    # Recursively call
    for reply in comment.replies:
        traverse_comments(reply, collected_comments, depth + 1, max_depth)


def get_all_comments_in_post(submission_id: str) -> str:
    """
    Collects all comments from a Reddit submission, including nested comments.
    This function replaces the 'more comments' objects with actual comments,
    traverses all top-level comments, and collects the text of all comments
    into a single string.

    Note: This method is not efficient for large threads with many comments.

    Args:
        submission (str): A Reddit submission id.
    Returns:
        str: A single string containing the text of all comments, separated by
        newline characters.
    """
    submission = REDDIT.submission(id=submission_id)

    submission.comment_sort = "best"

    # Replace the 'more comments' object with actual comments
    submission.comments.replace_more(limit=None)

    # List to store all comments' text
    all_comments = []

    # Traverse all top-level comments
    for top_level_comment in submission.comments:
        traverse_comments(top_level_comment, all_comments)

    # Join all comments into a single string
    return "\n".join(all_comments)
