from dotenv import load_dotenv
import io
import logging
import os
from sqlalchemy.orm import Session
import sys

from src import reddit, db
from src.db import RedditPosts

load_dotenv(override=True)
load_dotenv(f".env.{os.getenv('ENVIRONMENT')}", override=True)

CHUNK_SIZE = int(os.getenv('CHUNK_SIZE'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP'))

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
        db.insert_documents_from_comments_body(p['id'], CHUNK_SIZE, CHUNK_OVERLAP)
    else:
        logging.info(f'Reddit post already exists: {p["id"]}')
        
        if db.is_post_modified(p['id']):
            logging.info(f'Reddit post has been modified: {p["id"]}')
            
            logging.info(f'Deleting existing post: {p["id"]}')
            with Session(db.get_db_engine()) as session:
                session.query(RedditPosts).filter_by(id=p["id"]).delete()
                session.commit()

            logging.info(f'Inserting Reddit post: {p["id"]}')
            db.insert_reddit_post(p)
            db.insert_documents_from_comments_body(p['id'], CHUNK_SIZE, CHUNK_OVERLAP)

def insert_reddit_posts(posts: list[dict]):
    """Inserts a list of Reddit posts into the `posts` and `documents` tables."""
    for p in posts:
        logging.info('Processing Reddit post: %s', p["permalink"])

        if p["link_flair_text"] == "Meme":
            logging.info(f'Skipping Reddit post. Reason: Meme')
            continue

        insert_reddit_post_and_comments(p)

if __name__ == "__main__":

    posts = reddit.get_top_posts("dataengineering", limit=100, t="month")
    insert_reddit_posts(posts)

    posts = reddit.get_top_posts("dataengineering", limit=100, t="year")
    insert_reddit_posts(posts)

    posts_w_no_docs = db.get_posts_without_documents()
    if len(posts_w_no_docs) > 0:
        logging.info(f'Processing Reddit posts without documents: {len(posts_w_no_docs)}')
        
        for post_id in posts_w_no_docs:
            post = reddit.get_post_from_id(post_id)
            insert_reddit_post_and_comments(post)



    