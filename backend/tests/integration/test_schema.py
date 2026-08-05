import os

import psycopg
import pytest


def _connect() -> psycopg.Connection:
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql://paddockbook:paddockbook@localhost:5432/paddockbook",
    )
    return psycopg.connect(dsn)


@pytest.fixture(scope="module")
def conn():
    connection = _connect()
    yield connection
    connection.close()


def test_vector_extension_enabled(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
        assert cur.fetchone() is not None


def test_documents_table_columns(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'documents';
            """
        )
        columns = {row[0]: row[1] for row in cur.fetchall()}

    assert columns.get("id") == "uuid"
    assert columns.get("title") == "text"
    assert columns.get("created_at") == "timestamp with time zone"


def test_document_chunks_table_columns(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'document_chunks';
            """
        )
        columns = {row[0]: row[1] for row in cur.fetchall()}

    assert columns.get("id") == "uuid"
    assert columns.get("document_id") == "uuid"
    assert columns.get("chunk_text") == "text"
    assert columns.get("chunk_order") == "integer"
    assert columns.get("created_at") == "timestamp with time zone"
    assert "embedding" in columns
    assert "department" in columns


def test_embedding_column_is_1024_dimensional_vector(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT format_type(atttypid, atttypmod)
            FROM pg_attribute
            WHERE attrelid = 'document_chunks'::regclass
              AND attname = 'embedding';
            """
        )
        (type_repr,) = cur.fetchone()

    assert type_repr == "vector(1024)"


def test_department_enum_has_expected_values(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.enumlabel
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname = 'department'
            ORDER BY e.enumsortorder;
            """
        )
        values = [row[0] for row in cur.fetchall()]

    assert values == ["sporting", "technical", "financial"]


def test_document_chunks_references_documents(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT confrelid::regclass::text
            FROM pg_constraint
            WHERE conrelid = 'document_chunks'::regclass
              AND contype = 'f';
            """
        )
        referenced_tables = [row[0] for row in cur.fetchall()]

    assert "documents" in referenced_tables


def test_document_id_and_chunk_order_are_unique_together(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT array_agg(a.attname ORDER BY a.attname)
            FROM pg_constraint c
            JOIN unnest(c.conkey) AS k(attnum) ON true
            JOIN pg_attribute a
              ON a.attrelid = c.conrelid AND a.attnum = k.attnum
            WHERE c.conrelid = 'document_chunks'::regclass
              AND c.contype = 'u'
            GROUP BY c.oid;
            """
        )
        unique_groups = [set(row[0]) for row in cur.fetchall()]

    assert {"chunk_order", "document_id"} in unique_groups
