from dotenv import load_dotenv
import os
import requests


load_dotenv(override=True)


def get_top_post(subreddit: str, limit: int = 100, t: str = "month") -> dict:
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
        f"https://oauth.reddit.com/r/{subreddit}",
        headers={
            "Authorization": f"bearer {os.getenv('TOKEN')}",
            "User-Agent": os.getenv("USER_AGENT"),
        },
        params={"limit": limit, "t": t},
    )

    if response.status_code != 200:
        raise Exception(
            f"Failed to get top posts from {subreddit}. Error: {response.text}"
        )

    return response.json()
