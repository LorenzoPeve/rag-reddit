from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import logging
import os
from sqlalchemy.orm import Session
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import reddit, db
from src.db import RedditPosts

load_dotenv(".env.production", override=True)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


CHUNK_SIZE = int(os.getenv("CHUNK_SIZE"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP"))


def delete_post(post_id: str):
    logging.info(f"Deleting existing post: {post_id}")
    with Session(db.get_db_engine()) as session:
        session.query(RedditPosts).filter_by(id=post_id).delete()
        session.commit()


def insert_reddit_post_and_comments(p: dict) -> None:
    """
    Inserts a Reddit post and its comments into the `posts` and `documents`
    tables.

    If the post already exists and has been modified, the existing post is
    deleted and a new post is inserted. Otherwise, the post is skipped.
    """
    with Session(db.get_db_engine()) as session:
        db_post = session.query(RedditPosts).filter_by(id=p["id"]).first()

    if db_post is None:
        logging.info(f'Inserting Reddit post: {p["id"]}')
        db.insert_reddit_post(p)
        db.insert_documents_from_comments_body(p["id"], CHUNK_SIZE, CHUNK_OVERLAP)
    else:
        logging.info(f'Reddit post already exists: {p["id"]}')

        if not db.is_post_modified(p["id"]):
            logging.info(f'Skipping Reddit post: {p["id"]}. Already up-to-date.')
        else:
            logging.info(f'Reddit post has been modified: {p["id"]}')
            delete_post(p["id"])

            logging.info(f'Inserting Reddit post: {p["id"]}')
            db.insert_reddit_post(p)
            db.insert_documents_from_comments_body(p["id"], CHUNK_SIZE, CHUNK_OVERLAP)


def insert_reddit_posts(posts: list[dict]):
    """Inserts a list of Reddit posts into the `posts` and `documents` tables."""

    def process_post(p):
        logging.info(f'Processing Reddit post: {p["id"]}')

        if p["link_flair_text"] == "Meme":
            logging.info(f"Skipping Reddit post. Reason: Meme")
            return
        try:
            insert_reddit_post_and_comments(p)
        except Exception as e:
            logging.error(f"Error processing post: {p['id']}. Error: {e}")

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(process_post, p) for p in posts]

        for f in as_completed(futures):
            f.result()


def lambda_handler(event, context):
    logging.info("Lambda function starting")
    logging.info("Function starting")

    after = None
    for i in range(1, 10):
        logging.info(f"Fetching top posts from r/dataengineering {i}")
        posts = reddit.get_top_posts("dataengineering", limit=50, t="year", after=after)
        after = "t3_" + posts[-1]["id"]
        insert_reddit_posts(posts)
        time.sleep(10)

    logging.info("Function completed")


if __name__ == "__main__":
    lambda_handler(None, None)
