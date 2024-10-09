import hashlib
import os
import sqlalchemy
from sqlalchemy import Column, Integer, String, create_engine, text, ForeignKey
from sqlalchemy.orm import Session
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector

from src import reddit, openai


Base = declarative_base()


class RedditPosts(Base):
    __tablename__ = "posts"

    id = Column(String(32), primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)  # image posts have no description
    upvotes = Column(Integer, nullable=False)
    downvotes = Column(Integer, nullable=False)
    tag = Column(String(30), nullable=True)
    num_comments = Column(Integer, nullable=False)
    permalink = Column(String, nullable=False)
    content_hash = Column(String(32), nullable=False)

    def __repr__(self):
        return f"<RedditPost(id={self.id}, title={self.title})>"


class Documents(Base):

    __tablename__ = "documents"

    id = Column(String(32), primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)
    chunk_id = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=True)

    def __repr__(self):
        return f"<Document(id={self.id}, post_id={self.post_id}, chunk_id={self.chunk_id})>"


def init_schema() -> None:
    engine = get_db_engine()

    with Session(engine) as session:
        session.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        session.execute(text("CREATE SCHEMA public;"))
        session.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;")
        )
        session.commit()

    Base.metadata.create_all(engine)


def get_db_engine() -> sqlalchemy.engine.base.Engine:
    """
    Creates and returns a SQLAlchemy engine instance for connecting to a PostgreSQL database.
    The connection string is constructed using environment variables:
    - DB_USER: The username for the database.
    - DB_PASSWORD: The password for the database.
    - DB_HOST: The hostname of the database server.
    - DB_PORT: The port number on which the database server is listening.
    - DB_NAME: The name of the database.
    Returns:
        sqlalchemy.engine.base.Engine: A SQLAlchemy engine instance for the PostgreSQL database.
    """

    connection_string = (
        f'postgresql://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}'
        f'@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}'
    )

    return create_engine(connection_string)


def insert_reddit_post(p: dict) -> None:
    """
    Loads a Reddit post into the database.
    Args:
        p (dict): A dictionary containing the Reddit post data. The dictionary
                  should have the following keys:
                  - 'id': The unique identifier of the post.
                  - 'title': The title of the post.
                  - 'selftext': The body text of the post.
                  - 'ups': The number of upvotes the post received.
                  - 'downs': The number of downvotes the post received.
                  - 'link_flair_text': The tag or flair associated with the post.
                  - 'num_comments': The number of comments on the post.
                  - 'permalink': The permalink URL of the post.
    Returns:
        None
    """
    assert type(p) == dict
    engine = get_db_engine()

    # Get all comments in the post and calculate the hash value
    # DEV NOTE: This allows us to check if the post has been modified
    comments = reddit.get_all_comments_in_post(p["id"])
    body = p["title"] + p["selftext"] + comments
    content_hash = hashlib.md5(body.encode()).hexdigest()

    # Manipulate description
    text = p["selftext"]
    if len(text) == 0:
        text = None

    # Insert the post into the database
    with Session(engine) as session:
        post = RedditPosts(
            id=p["id"],
            title=p["title"],
            description=text,
            upvotes=p["ups"],
            downvotes=p["downs"],
            tag=p["link_flair_text"],
            num_comments=p["num_comments"],
            permalink=p["permalink"],
            content_hash=content_hash,
        )
        session.add(post)
        session.commit()


def insert_documents_from_comments_body(post_id: str) -> None:
    """
    Inserts the comments body into the database. If the comments body exceeds
    the token limit, the body is split into chunks and each chunk is inserted
    as a separate document.

    Args:
        post_id (str): The unique identifier of the post.
    Returns:
        None
    """
    chunk_size = os.getenv("CHUNK_SIZE")
    chunk_overlap = os.getenv("CHUNK_OVERLAP")
    engine = get_db_engine()
    comments = reddit.get_all_comments_in_post(post_id)

    with Session(engine) as session:
        post = session.query(RedditPosts).filter_by(id=post_id).first()

    document_body = f"{post.title}\n{post.description}\n{comments}"
    tokens = openai.get_tokens_from_string(document_body)

    if len(tokens) <= chunk_size:
        with Session(engine) as session:
            d = Documents(
                id=f"{post_id}_1", post_id=post_id, chunk_id=1, content=document_body
            )
            session.add(d)
            session.commit()
    else:
        start = 0
        end = chunk_size
        chunk_id = 1

        while end < len(tokens):
            chunk_tokens = tokens[start:end]

            # Insert the document chunk into the database
            with Session(engine) as session:
                d = Documents(
                    id=f"{post_id}_{chunk_id}",
                    post_id=post_id,
                    chunk_id=start,
                    content=openai.get_string_from_tokens(chunk_tokens),
                )
                session.add(d)
                session.commit()

            # Update start and end with overlap
            start += chunk_size - chunk_overlap
            end += chunk_size - chunk_overlap
            chunk_id += 1


def is_post_modified(post_id: str) -> bool:
    """ """
    with Session(get_db_engine()) as session:
        post = session.query(RedditPosts).filter_by(id=post_id).first()

    # comnpare number of comments

    # compare title or description

    # if nothing change, return False

    # lastly, query comments and calculate hash value
    pass
