from dotenv import load_dotenv
import logging
import os
from sqlalchemy.orm import Session
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src import reddit, db
from src.db import RedditPosts

load_dotenv(override=True)
load_dotenv(f".env.{os.getenv('ENVIRONMENT')}", override=True)

CHUNK_SIZE = int(os.getenv('CHUNK_SIZE'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP'))

def delete_post(post_id: str):
    logging.info(f'Deleting existing post: {post_id}')
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

        if db.is_post_modified(p["id"]):
            logging.info(f'Reddit post has been modified: {p["id"]}')
            delete_post(p["id"])

            logging.info(f'Inserting Reddit post: {p["id"]}')
            db.insert_reddit_post(p)
            db.insert_documents_from_comments_body(p["id"], CHUNK_SIZE, CHUNK_OVERLAP)

def insert_reddit_posts(posts: list[dict]):
    """Inserts a list of Reddit posts into the `posts` and `documents` tables."""
    for p in posts:
        logging.info("Processing Reddit post: %s", p["permalink"])

        if p["link_flair_text"] == "Meme":
            logging.info(f"Skipping Reddit post. Reason: Meme")
            continue
        try:
            insert_reddit_post_and_comments(p)
        except Exception as e:
            logging.error(f"Error processing post: {p['permalink']}. Error: {e}")
            delete_post(p["id"])

if __name__ == "__main__":

    logging.info("Starting ETL process")
    posts = reddit.get_top_posts("dataengineering", limit=100, t="month")
    after = 't3_' + posts[-1]['id']
    insert_reddit_posts(posts)

    # logging.info(f"Fetching more posts - after: {after}")
    # posts = reddit.get_top_posts("dataengineering", limit=100, t="month", after=after)
    # after = 't3_' + posts[-1]['id']
    # insert_reddit_posts(posts)

    # logging.info(f"Fetching more posts - after: {after}")
    # posts = reddit.get_top_posts("dataengineering", limit=100, t="month", after=after)
    # after = 't3_' + posts[-1]['id']
    # insert_reddit_posts(posts)

    # logging.info(f"Fetching more posts - after: {after}")
    # posts = reddit.get_top_posts("dataengineering", limit=100, t="month", after=after)
    # after = 't3_' + posts[-1]['id']
    # insert_reddit_posts(posts)
    # posts = reddit.get_top_posts("dataengineering", limit=100, t="year")
    # insert_reddit_posts(posts)


    