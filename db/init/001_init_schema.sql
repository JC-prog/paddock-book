-- Local vector database schema for regulation document chunks.
-- Runs automatically on first container startup via
-- /docker-entrypoint-initdb.d/. See specs/005-pgvector-local-dev/data-model.md
-- and contracts/schema.md for the design this implements.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TYPE department AS ENUM ('sporting', 'technical', 'financial');

CREATE TABLE documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE document_chunks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES documents (id),
    chunk_text text NOT NULL,
    embedding vector(1024) NOT NULL,
    department department NOT NULL,
    chunk_order integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_id, chunk_order)
);
