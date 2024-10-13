from dotenv import load_dotenv
import json
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import reddit, db, openai
from src.db import RedditPosts

ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')

load_dotenv(f".env.{ENVIRONMENT}", override=True)

CHUNK_SIZE = int(os.getenv('CHUNK_SIZE'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP'))


def load_posts():

    posts = reddit.get_top_posts('dataengineering', limit=100, t='month')

    for p in posts:

        print(p['permalink'])

        if p['link_flair_text'] == 'Meme':
            continue

        db.insert_reddit_post(p)
        db.insert_documents_from_comments_body(p['id'], CHUNK_SIZE, CHUNK_OVERLAP)

      

if __name__ == "__main__":

    db.init_schema()
    load_posts()