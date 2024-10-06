from dotenv import load_dotenv
import os
import praw
import requests
from requests.auth import HTTPBasicAuth


load_dotenv(override=True)

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


def get_top_posts(subreddit: str, limit: int = 100, t: str = "month") -> list[dict]:
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
        params={"limit": limit, "t": t},
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


def traverse_comments(comment: praw.models.Comment, collected_comments: list):
    """
    Recursively traverses a comment tree and collects the comment bodies into a list.
        comment (praw.models.Comment): The current Reddit comment object.
        collected_comments (list): A list to collect the comments' body text.
    Returns:
        None: The function modifies the collected_comments list in place.
    """
    # Skip comments made by the bot
    if "I am a bot, and this action was performed automatically" in comment.body:
        return

    # Add the current comment's body to the list
    discard = [
        "following",
        "following!",
        "+1",
        "[deleted]",
        "deleted",
    ]

    if comment.body.lower() not in discard:
        collected_comments.append(comment.body)

    # Recursively traverse replies if they exist
    for reply in comment.replies:
        traverse_comments(reply, collected_comments)


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
