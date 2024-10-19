from dotenv import load_dotenv
import io
import logging
import os
from sqlalchemy.orm import Session
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import reddit, db
from src.db import RedditPosts

load_dotenv(override=True)
load_dotenv(f".env.{os.getenv('ENVIRONMENT')}", override=True)

CHUNK_SIZE = int(os.getenv('CHUNK_SIZE'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP'))

log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    format=log_format,
    level=logging.INFO,
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("test_app.log", mode="w", encoding='utf-8'),
    ],
)
logger = logging.getLogger(__name__)


def insert_reddit_post(p: dict):
    with Session(db.get_db_engine()) as session:
        db_post = session.query(RedditPosts).filter_by(id=p["id"]).first()

    if db_post is None:
        logger.info(f'Inserting Reddit post: {p["id"]}')
        db.insert_reddit_post(p)
        db.insert_documents_from_comments_body(p['id'], CHUNK_SIZE, CHUNK_OVERLAP)
    else:
        logger.info(f'Reddit post already exists: {p["id"]}')
        
        if db.is_post_modified(p['id']):
            logger.info(f'Reddit post has been modified: {p["id"]}')
            
            logger.info(f'Deleting existing post: {p["id"]}')
            with Session(db.get_db_engine()) as session:
                session.query(RedditPosts).filter_by(id=p["id"]).delete()
                session.commit()

            logger.info(f'Inserting Reddit post: {p["id"]}')
            db.insert_reddit_post(p)
            db.insert_documents_from_comments_body(p['id'], CHUNK_SIZE, CHUNK_OVERLAP)

def insert_reddit_posts(posts: list[dict]):
    for p in posts:
        logger.info('Processing Reddit post: %s', p["permalink"])

        if p["link_flair_text"] == "Meme":
            logger.info(f'Skipping Reddit post. Reason: Meme')
            continue

        insert_reddit_post(p)

if __name__ == "__main__":

    posts = reddit.get_top_posts("dataengineering", limit=100, t="month")
    insert_reddit_posts(posts)

    posts = reddit.get_top_posts("dataengineering", limit=100, t="year")
    insert_reddit_posts(posts)

    posts_w_no_docs = db.get_posts_without_documents()
    if len(posts_w_no_docs) > 0:
        logger.info(f'Processing Reddit posts without documents: {len(posts_w_no_docs)}')
        
        for post_id in posts_w_no_docs:
            post = reddit.get_post(post_id)
            insert_reddit_post(post)

