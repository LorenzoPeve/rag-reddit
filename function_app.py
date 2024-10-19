import azure.functions as func
from dotenv import load_dotenv
import logging
import os
from sqlalchemy.orm import Session

from src import reddit, db
from src.db import RedditPosts

load_dotenv(".env.dev", override=True)

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

app = func.FunctionApp()

@app.schedule(schedule="0 0 * * * *", arg_name="myTimer", run_on_startup=True,
              use_monitor=False) 
def get_reddit_comments(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function executed.')