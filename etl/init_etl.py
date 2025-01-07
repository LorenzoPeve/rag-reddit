from src import reddit, db, rag
from datetime import datetime
import json
import os
from sqlalchemy.orm import Session
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def get_posts(n: int):
    posts = reddit.get_top_posts("dataengineering", limit=n, t="all")
    out = []
    for post in posts:
        p = reddit.get_post_from_id(post["id"])
        if p['tag'] == 'Meme':
            continue
        comments = reddit.get_all_comments_in_post(post["id"])
        p['comments'] = comments
        p['content_hash'] = db.get_content_hash(
            p["title"], p["description"], comments)
        out.append(p)
    return out


def get_chunks_with_embeddings(post: dict):

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
            chunk_content = f"{post.title}\n{chunk_content}"

    return dict(
        id=f"{post['post_id']}_{chunk_id}",
        post_id=post['post_id'],
        chunk_id=chunk_id,
        content=chunk_content,
        embedding=rag.llm_client.get_embedding(chunk_content),
    )


if __name__ == '__main__':

    db.init_schema()
    posts = get_posts(15)
    with open("posts_dev.json", "w") as f:
        json.dump(posts, f, indent=4)
