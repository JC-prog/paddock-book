import os
import uuid

import psycopg
import pytest

from src.modules.eval.repository import list_documents_with_chunks


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


def _format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


def _seed_document(conn, department: str, chunk_texts: list[str]) -> str:
    title = f"Eval Repository Test Document {uuid.uuid4()}"
    vector = _format_vector([1.0] * 1024)
    with conn.cursor() as cur:
        cur.execute("INSERT INTO documents (title) VALUES (%s) RETURNING id", (title,))
        (document_id,) = cur.fetchone()
        for order, text in enumerate(chunk_texts):
            cur.execute(
                """
                INSERT INTO document_chunks (document_id, chunk_text, embedding, department, chunk_order)
                VALUES (%s, %s, %s::vector, %s, %s)
                """,
                (document_id, text, vector, department, order),
            )
    conn.commit()
    return title


def _cleanup(titles: list[str]) -> None:
    with _connect() as cleanup_conn:
        with cleanup_conn.cursor() as cur:
            for title in titles:
                cur.execute(
                    "DELETE FROM document_chunks WHERE document_id = "
                    "(SELECT id FROM documents WHERE title = %s)",
                    (title,),
                )
                cur.execute("DELETE FROM documents WHERE title = %s", (title,))
        cleanup_conn.commit()


def test_returns_every_document_in_the_department_with_chunks_in_order(conn):
    title = _seed_document(conn, "sporting", ["First chunk.", "Second chunk.", "Third chunk."])

    try:
        result = list_documents_with_chunks(conn, "sporting")

        assert title in result
        assert result[title] == ["First chunk.", "Second chunk.", "Third chunk."]
    finally:
        _cleanup([title])


def test_returns_every_document_currently_ingested_in_the_department(conn):
    title_a = _seed_document(conn, "technical", ["A."])
    title_b = _seed_document(conn, "technical", ["B."])

    try:
        result = list_documents_with_chunks(conn, "technical")

        assert title_a in result
        assert title_b in result
    finally:
        _cleanup([title_a, title_b])


def test_returns_nothing_for_a_department_with_no_ingested_documents(conn):
    result = list_documents_with_chunks(conn, "financial")

    assert result == {}


def test_never_returns_another_departments_documents(conn):
    sporting_title = _seed_document(conn, "sporting", ["Sporting content."])
    technical_title = _seed_document(conn, "technical", ["Technical content."])

    try:
        result = list_documents_with_chunks(conn, "sporting")

        assert sporting_title in result
        assert technical_title not in result
    finally:
        _cleanup([sporting_title, technical_title])
