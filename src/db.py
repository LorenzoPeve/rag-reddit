from datetime import datetime, timezone
import hashlib
import logging
import os
import sqlalchemy
from sqlalchemy import (
    Column,
    Integer,
    String,
    create_engine,
    text,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import (
    Session,
    declarative_base,
    Mapped,
    mapped_column,
    relationship,
)
from pgvector.sqlalchemy import Vector
import psycopg

from src import reddit, rag

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


connection_string = (
    f'postgresql+psycopg://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}'
    f'@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}'
)
engine = create_engine(connection_string, pool_size=20)
llm_client = rag.ThrottledOpenAI()

Base = declarative_base()


class RedditPosts(Base):
    __tablename__ = "posts"

    id = Column(String(32), primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)  # image posts have no description
    score = Column(Integer, nullable=False)
    upvotes = Column(Integer, nullable=False)
    downvotes = Column(Integer, nullable=False)
    tag = Column(String(30), nullable=True)
    num_comments = Column(Integer, nullable=False)
    permalink = Column(String, nullable=False)
    content_hash = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False)
    last_updated_at = Column(DateTime, nullable=False)

    documents = relationship(
        "Documents", back_populates="post", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<RedditPost(id={self.id}, title={self.title})>"


class Documents(Base):

    __tablename__ = "documents"

    id = Column(String(32), primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=True)

    post = relationship("RedditPosts", back_populates="documents")

    def __repr__(self):
        return f"<Document(id={self.id}, post_id={self.post_id}, chunk_id={self.chunk_id})>"


def get_cursor():
    """
    Connects to the PostgreSQL database using psycopg and returns the connection and cursor objects.
    The connection parameters are retrieved from environment variables.

    Returns:
        conn: The connection object to the PostgreSQL database.
        cur: The cursor object for executing SQL queries.
    """
    conn = psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )
    return conn.cursor()


def init_schema() -> None:

    with Session(engine) as session:
        session.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        session.execute(text("CREATE SCHEMA public;"))
        session.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;")
        )
        session.commit()

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.execute(
            text(
                """
            ALTER TABLE documents
            ADD COLUMN content_ts_vector tsvector
            GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
        """
            )
        )

        # Adding indexes for full-text search and vector search
        session.execute(
            text(
                """
            CREATE INDEX content_ts_vector_idx ON documents USING GIN (content_ts_vector);
            CREATE INDEX embedding_idx ON documents USING hnsw (embedding vector_cosine_ops);
        """
            )
        )
        session.commit()


def get_content_hash(title: str, description: str, body: str) -> str:
    """
    Calculates the hash value of the post content.

    Args:
        title (str): The title of the post.
        description (str): The description of the post.
        body (str): The body text of the post.
    Returns:
        str: The hash value of the post content.
    """
    content = title + description + body
    return hashlib.md5(content.encode()).hexdigest()


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

    # Get all comments in the post and calculate the hash value
    # DEV NOTE: This allows us to check if the post has been modified
    comments = reddit.get_all_comments_in_post(p["id"])
    content_hash = get_content_hash(p["title"], p["selftext"], comments)

    now = datetime.now(timezone.utc)
    now = now.replace(microsecond=0)

    # Insert the post into the database
    with Session(engine) as session:
        post = RedditPosts(
            id=p["id"],
            title=p["title"],
            description=p["selftext"],
            score=p["score"],
            upvotes=p["ups"],
            downvotes=p["downs"],
            tag=p["link_flair_text"],
            num_comments=p["num_comments"],
            permalink=p["permalink"],
            content_hash=content_hash,
            created_at=datetime.fromtimestamp(p["created"]),
            last_updated_at=now,
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

    with Session(engine) as session:
        post = session.query(RedditPosts).filter_by(id=post_id).first()

    # Generate entire document body as title + description + comments
    comments = reddit.get_all_comments_in_post(post_id)
    document_body = f"{post.title}\n{post.description}\n{comments}"

    # Split the document body into chunks
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

        # Insert the document chunk into the database
        with Session(engine) as session:
            d = Documents(
                id=f"{post_id}_{chunk_id}",
                post_id=post_id,
                chunk_id=chunk_id,
                content=chunk_content,
                embedding=llm_client.get_embedding(chunk_content),
            )
            session.add(d)
            session.commit()


def get_posts_url(ids: list[str]) -> dict[str, str]:
    """
    Returns the URLs of the Reddit posts based on the provided document IDs.
    """
    with Session(engine) as session:
        parent_posts = (
            session.query(RedditPosts)
            .filter(RedditPosts.id.in_(ids))
            .order_by(RedditPosts.id.asc())
            .all()
        )

    return {post.id: post.permalink for post in parent_posts}


def vector_search(text_query: str, limit: int) -> list[tuple]:
    """
    Returns the id and rank of the most semantically similar documents to the
    input text query.
    """
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
    vector = llm_client.get_embedding(text_query)
    cursor = get_cursor()
    cursor.execute(query, {"vector": vector, "limit": limit})
    result = cursor.fetchall()
    cursor.close()
    return result


def keyword_search(text_query: str, limit: int) -> list[tuple]:
    """Performns full-text search on the content of the documents."""
    query = """
    WITH ts_query AS (
        SELECT replace(plainto_tsquery(%(text_query)s)::text, '&', '|') AS modified_query
    )
    SELECT
        id,
        RANK () OVER (
            ORDER BY ts_rank_cd(
                content_ts_vector,
                to_tsquery('english', (SELECT modified_query FROM ts_query))
            ) DESC
        ) AS rank
    FROM documents
    WHERE
        content_ts_vector @@
        to_tsquery('english', (SELECT modified_query FROM ts_query))
    ORDER BY rank
    LIMIT %(limit)s;
    """
    cursor = get_cursor()
    cursor.execute(query, {"text_query": text_query, "limit": limit})
    result = cursor.fetchall()
    cursor.close()
    return result


def keyword_search_match_all(text_query: str, limit: int) -> list[tuple]:
    """
    Performs a full-text search on the content of the documents where all the
    words in the query must be present in the document.
    """
    query = """
    SELECT
        id,
        RANK () OVER (
            ORDER BY ts_rank_cd(
                content_ts_vector,
                plainto_tsquery('english', %(text_query)s)
            ) DESC
        ) AS rank
    FROM documents
    WHERE
        content_ts_vector @@
        plainto_tsquery('english', %(text_query)s)
    ORDER BY rank
    LIMIT %(limit)s;
    """
    cursor = get_cursor()
    cursor.execute(query, {"text_query": text_query, "limit": limit})
    result = cursor.fetchall()
    cursor.close()
    return result


def hybrid_search(text_query: str, limit: int) -> list[tuple]:
    """
    Performs a hybrid search. Hybrid search combines:
        - vector search
        - full-text search for exact matches
        - full-text search for partial matches

    using both full-text search and vector search.
    """
    keyword_results = keyword_search(text_query, limit)
    vector_results = vector_search(text_query, limit)
    exact_keyword_results = keyword_search_match_all(text_query, limit)

    # Convert results into a format suitable for use in a SQL query
    keyword_query = ", ".join([f"('{id}', {rank})" for id, rank in keyword_results])
    vector_query = ", ".join([f"('{id}', {rank})" for id, rank in vector_results])
    exact_keyword_query = ", ".join(
        [f"('{id}', {rank})" for id, rank in exact_keyword_results]
    )

    # Address edge case where no results are returned for exact keyword search
    if len(exact_keyword_query) == 0:
        exact_keyword_query = "('null', 0)"
        k_vector, k_fs, k_exact = 60, 60, 60
    else:
        k_vector, k_fs, k_exact = 60, 60 * 3, 60

    hybrid_query = f"""
        WITH vector_search AS (
            SELECT *
            FROM (VALUES {vector_query}) AS v(id, rank)
        ),
        fulltext_search AS (
            SELECT *
            FROM (VALUES {keyword_query}) AS k(id, rank)
        ),
        exact_fulltext_search AS (
            SELECT *
            FROM (VALUES {exact_keyword_query}) AS k(id, rank)
            WHERE id != 'null'
        ),
        hybrid_search AS (
            SELECT
                COALESCE(vector_search.id, fulltext_search.id, exact_fulltext_search.id) AS id,
                COALESCE(1.0 / (%(k_vector)s + vector_search.rank), 0.0) +
                COALESCE(1.0 / (%(k_fs)s + fulltext_search.rank), 0.0) +
                COALESCE(1.0 / (%(k_exact)s + exact_fulltext_search.rank), 0.0) AS score
            FROM vector_search
            FULL OUTER JOIN fulltext_search ON vector_search.id = fulltext_search.id
            FULL OUTER JOIN exact_fulltext_search ON vector_search.id = exact_fulltext_search.id
            ORDER BY score DESC
        )
        SELECT hybrid_search.id, documents.post_id, title, hybrid_search.score, content
        FROM hybrid_search
        LEFT JOIN documents ON hybrid_search.id = documents.id
        LEFT JOIN posts ON documents.post_id = posts.id
        ORDER BY score DESC
        LIMIT %(limit)s;
    """

    cursor = get_cursor()
    cursor.execute(
        hybrid_query,
        {"k_vector": k_vector, "k_fs": k_fs, "k_exact": k_exact, "limit": limit},
    )
    result = cursor.fetchall()
    cursor.close()
    return result


def is_post_modified(post_id: str) -> bool:
    """
    Returns True if a Reddit post has been modified since it was loaded into the database.
    """
    logger.info(f"Checking if post {post_id} has been modified.")
    with Session(engine) as session:
        db_post = session.query(RedditPosts).filter_by(id=post_id).first()

    reddit_post = reddit.get_post_from_id(post_id)

    # Check if the number of comments has changed
    logger.info(
        f"Checking number of comments. Reddit: {reddit_post['num_comments']}, DB: {db_post.num_comments}"
    )
    if reddit_post["num_comments"] != db_post.num_comments:
        return True

    # Check if the content hash has changed
    comments = reddit.get_all_comments_in_post(post_id)
    content_hash = get_content_hash(
        reddit_post["title"], reddit_post["description"], comments
    )

    logger.info(
        f"Checking content hash. Reddit: {content_hash}, DB: {db_post.content_hash}"
    )

    if content_hash != db_post.content_hash:
        return True
    return False


def get_posts_without_documents() -> list[RedditPosts]:
    """
    Iterates over all posts and returns posts that do not have any associated documents.

    Returns:
        list[RedditPosts]: A list of RedditPosts objects that do not have any associated documents.
    """

    with Session(engine) as session:
        posts_without_docs = (
            session.query(RedditPosts)
            .outerjoin(Documents)
            .filter(Documents.id == None)
            .all()
        )

    return [post.id for post in posts_without_docs]
