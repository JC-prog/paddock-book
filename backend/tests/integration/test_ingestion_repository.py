import os
import uuid

import psycopg
import pytest

from src.modules.ingestion.embeddings import EmbeddedChunk
from src.modules.ingestion.repository import title_exists, write_document


def _connect() -> psycopg.Connection:
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql://paddockbook:paddockbook@localhost:5432/paddockbook",
    )
    return psycopg.connect(dsn)


@pytest.fixture
def conn():
    connection = _connect()
    yield connection
    connection.rollback()
    connection.close()


def _unique_title() -> str:
    return f"Integration Test Document {uuid.uuid4()}"


def _cleanup(title: str) -> None:
    with _connect() as cleanup_conn:
        with cleanup_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM document_chunks WHERE document_id = "
                "(SELECT id FROM documents WHERE title = %s)",
                (title,),
            )
            cur.execute("DELETE FROM documents WHERE title = %s", (title,))
        cleanup_conn.commit()


def test_title_exists_is_false_for_an_unused_title(conn):
    assert title_exists(conn, _unique_title()) is False


def test_title_exists_is_true_after_writing_a_document(conn):
    title = _unique_title()
    chunks = [EmbeddedChunk(text="Some text.", order=0, embedding=[0.1] * 1024)]

    write_document(conn, title, "sporting", chunks)
    conn.commit()

    try:
        assert title_exists(conn, title) is True
    finally:
        _cleanup(title)


def test_write_document_writes_one_document_and_all_chunks(conn):
    title = _unique_title()
    chunks = [
        EmbeddedChunk(text="First chunk.", order=0, embedding=[0.1] * 1024),
        EmbeddedChunk(text="Second chunk.", order=1, embedding=[0.2] * 1024),
    ]

    write_document(conn, title, "technical", chunks)
    conn.commit()

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM documents WHERE title = %s", (title,))
            row = cur.fetchone()
            assert row is not None
            document_id = row[0]

            cur.execute(
                "SELECT chunk_order, department, chunk_text FROM document_chunks "
                "WHERE document_id = %s ORDER BY chunk_order",
                (document_id,),
            )
            rows = cur.fetchall()

        assert [r[0] for r in rows] == [0, 1]
        assert all(r[1] == "technical" for r in rows)
        assert [r[2] for r in rows] == ["First chunk.", "Second chunk."]
    finally:
        _cleanup(title)


def test_write_document_leaves_no_rows_when_a_write_fails_partway_through(conn):
    title = _unique_title()
    chunks = [
        EmbeddedChunk(text="First chunk.", order=0, embedding=[0.1] * 1024),
        EmbeddedChunk(text="Second chunk.", order=1, embedding=[0.1] * 5),  # wrong dimension
    ]

    with pytest.raises(Exception):
        write_document(conn, title, "financial", chunks)
    conn.rollback()

    with _connect() as check_conn:
        with check_conn.cursor() as cur:
            cur.execute("SELECT id FROM documents WHERE title = %s", (title,))
            assert cur.fetchone() is None
