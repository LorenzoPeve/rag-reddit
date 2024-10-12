import hashlib
import os
import sqlalchemy
from sqlalchemy import Column, Integer, String, create_engine, text, ForeignKey, select
from sqlalchemy.orm import Session, declarative_base, Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from src import reddit, openai
import psycopg2
from psycopg2 import extensions


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


def get_cursor():
    """
    Connects to the PostgreSQL database using psycopg2 and returns the connection and cursor objects.
    The connection parameters are retrieved from environment variables.

    Returns:
        conn: The connection object to the PostgreSQL database.
        cur: The cursor object for executing SQL queries.
    """
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )
    return conn.cursor()


def init_schema() -> None:
    engine = get_db_engine()

    with Session(engine) as session:
        # Drop and recreate the schema
        session.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        session.execute(text("CREATE SCHEMA public;"))
        
        # Create the vector extension (if not exists)
        session.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;")
        )
        session.commit()  # Commit schema changes before creating tables

    # Create all tables from metadata
    Base.metadata.create_all(engine)

    # Now that the tables exist, we can alter the table to add the column
    with Session(engine) as session:
        session.execute(text("""
            ALTER TABLE documents
            ADD COLUMN content_ts_vector tsvector
            GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
        """))

        session.execute(text("""
                             CREATE INDEX content_ts_vector_idx ON documents USING GIN (content_ts_vector);
                             """))
        



        session.commit()




  


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
    Loads a Reddit post into the database. Internally, this function calculates
    the hash value of the post content and stores it in the database. This hash
    value can be used to check if the post has been modified since it was loaded
    into the database.

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

    # Insert the post into the database
    with Session(engine) as session:
        post = RedditPosts(
            id=p["id"],
            title=p["title"],
            description=p["selftext"],
            upvotes=p["ups"],
            downvotes=p["downs"],
            tag=p["link_flair_text"],
            num_comments=p["num_comments"],
            permalink=p["permalink"],
            content_hash=content_hash,
        )
        session.add(post)
        session.commit()


def insert_documents_from_comments_body(
    post_id: str, chunk_size: int, chunk_overlap: int
) -> None:
    """
    Inserts the comments body into the database. If the comments body exceeds
    the token limit, the body is split into chunks and each chunk is inserted
    as a separate document.

    Args:
        post_id (str): The unique identifier of the post.
    Returns:
        None
    """
    engine = get_db_engine()

    with Session(engine) as session:
        post = session.query(RedditPosts).filter_by(id=post_id).first()

    # Generate entire document body as title + description + comments
    comments = reddit.get_all_comments_in_post(post_id)
    document_body = f"{post.title}\n{post.description}\n{comments}"

    # Split the document body into chunks
    tokens = openai.get_tokens_from_string(document_body)
    num_chunks = (
        len(tokens) + chunk_size - 1
    ) // chunk_size  # Calculate the number of chunks

    for chunk_id in range(1, num_chunks + 1):
        start = (chunk_id - 1) * (chunk_size - chunk_overlap)
        end = start + chunk_size
        chunk_content = openai.get_string_from_tokens(tokens[start:end])

        # Prepend the title to all chunks except the first one
        if chunk_id != 1:
            chunk_content = f"{post.title}\n{chunk_content}"

        # Insert the document chunk into the database
        with Session(engine) as session:
            d = Documents(
                id=f"{post_id}_{chunk_id}",
                post_id=post_id,
                chunk_id=chunk_id,
                content=chunk_content,
                embedding=openai.get_embedding(chunk_content),
            )
            session.add(d)
            session.commit()


def vector_search(text_query: str, limit: int) -> list[tuple]:
    """Returns the most similar records to the given vector."""

    # NOTE: Casting for vector type https://github.com/pgvector/pgvector-python/issues/4
    # The smaller the cosine distance, the more semantically similar two vectors are.
    # Partial results are
    # ('1ftama5_1', 0.39604451632764925, 1)
    # ('1fv6hi1_3', 0.3967565950831704, 2)
    query = """
    SELECT id, RANK () OVER (ORDER BY embedding <=> %(vector)s::vector) AS rank
    FROM documents
    ORDER BY embedding <=> %(vector)s::vector ASC
    LIMIT %(limit)s;
    """
    vector = openai.get_embedding(text_query)
    cursor = get_cursor()
    cursor.execute(query, {"vector": vector, "limit": limit})
    result = cursor.fetchall()
    cursor.close()
    return result

def keywork_search(text_query: str, limit: int) -> list[tuple]:
    pass





def is_post_modified(post_id: str) -> bool:
    """ """
    with Session(get_db_engine()) as session:
        post = session.query(RedditPosts).filter_by(id=post_id).first()

    # comnpare number of comments

    # compare title or description

    # if nothing change, return False

    # lastly, query comments and calculate hash value
    pass
