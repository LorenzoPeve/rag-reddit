from datetime import datetime
import json
import os
from sqlalchemy.orm import Session
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import reddit, db, rag

def get_posts(n: int):
    posts = reddit.get_top_posts("dataengineering", limit=n, t="all")
    out = []
    for post in posts:
        p = reddit.get_post_from_id(post["id"])
        if p['tag'] == 'Meme':
            continue
        comments = reddit.get_all_comments_in_post(post["id"])
        p['comments'] = comments
        p['content_hash'] = db.get_content_hash(p["title"], p["description"], comments)
        out.append(p)
    return out


def get_chunks_with_embeddings(post: dict) -> dict:
    """
    Returns a dictionary containing the required attributes for a `db.Documents` object.
    """
    assert 'title' in post
    assert 'description' in post
    assert 'comments' in post
    chunk_size = 1200
    chunk_overlap = 120

    document_body = f"{post['title']}\n{post['description']}\n{post['comments']}"

    tokens = rag.get_tokens_from_string(document_body)
    num_chunks = (
        len(tokens) + chunk_size - 1
    ) // chunk_size  # Calculate the number of chunks

    for chunk_id in range(1, num_chunks + 1):
        start = (chunk_id - 1) * (chunk_size - chunk_overlap)
        end = start + chunk_size
        chunk_content = rag.get_string_from_tokens(tokens[start:end])

        # Prepend the title to all chunks except the first one
        if chunk_id != 1:
            chunk_content = f"{post['title']}\n{chunk_content}"

    return dict(
        id=f"{post['id']}_{chunk_id}",
        post_id=post['id'],
        chunk_id=chunk_id,
        content=chunk_content,
        embedding=rag.ThrottledOpenAI().get_embedding(chunk_content),
    )


if __name__ == '__main__':

    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "data")

    if 'posts_dev.json' in os.listdir(data_dir) and 'chunks_dev.json' in os.listdir(data_dir):
        print("Data already loaded.")
        sys.exit(0)

    db.init_schema()

    # Get posts ###############################################################
    posts = get_posts(200)
    with open("posts_dev.json", "w") as f:
        json.dump(posts, f, indent=4)

    # Load posts to DB
    for i, post in enumerate(posts):
        print(f'Loading Post {i+1} of {len(posts)}')
        with Session(db.engine) as session:
            post = db.RedditPosts(
                id=post["id"],
                title=post["title"],
                description=post["description"],
                score=post["score"],
                upvotes=post["upvotes"],
                downvotes=post["downvotes"],
                tag=post["tag"],
                num_comments=post["num_comments"],
                permalink=post["permalink"],
                content_hash=post["content_hash"],
                created_at=datetime.fromtimestamp(post["created"]),
                last_updated_at=datetime(2025, 1, 1)
            )
            session.add(post)
            session.commit()

    # Get chunks with embeddings ##############################################
    chunks = []
    for post in posts:
        chunks.append(get_chunks_with_embeddings(post))

    with open("chunks_dev.json", "w") as f:
        json.dump(chunks, f, indent=4)

    # Load chunks to DB
    for i, chunk in enumerate(chunks):
        print(f'Loading Chunk {i+1} of {len(chunks)}')
        with Session(db.engine) as session:
            chunk = db.Documents(
                id=chunk["id"],
                post_id=chunk["post_id"],
                chunk_id=chunk["chunk_id"],
                content=chunk["content"],
                embedding=chunk["embedding"],
            )
            session.add(chunk)
            session.commit()