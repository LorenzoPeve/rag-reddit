-- This script is run when the database container is started
-- Drop the public schema and create a new one
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

-- Create the posts table
CREATE TABLE posts (
    id VARCHAR(32) NOT NULL, 
    title VARCHAR NOT NULL, 
    description VARCHAR, 
    score INTEGER NOT NULL, 
    upvotes INTEGER NOT NULL, 
    downvotes INTEGER NOT NULL, 
    tag VARCHAR(30), 
    num_comments INTEGER NOT NULL, 
    permalink VARCHAR NOT NULL, 
    content_hash VARCHAR(32) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    last_updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

-- Create the comments table
CREATE TABLE documents (
    id VARCHAR(32) NOT NULL, 
    post_id VARCHAR(32) NOT NULL, 
    chunk_id INTEGER NOT NULL, 
    content VARCHAR NOT NULL, 
    embedding VECTOR(1536), 
    PRIMARY KEY (id), 
    FOREIGN KEY(post_id) REFERENCES posts (id) ON DELETE CASCADE
);

ALTER TABLE documents
ADD COLUMN content_ts_vector tsvector
GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

CREATE INDEX content_ts_vector_idx ON documents USING GIN (content_ts_vector);
CREATE INDEX embedding_idx ON documents USING hnsw (embedding vector_cosine_ops);