import os
import uuid

import psycopg
import pytest

from src.modules.chat.retrieval import retrieve_relevant_chunks


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


def _seed_chunk(conn, department: str, chunk_text: str, embedding: list[float]) -> str:
    """Seeds one document (with a fresh, unique title) plus one chunk. Returns the title."""
    title = f"Retrieval Test Document {uuid.uuid4()}"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (title) VALUES (%s) RETURNING id",
            (title,),
        )
        (document_id,) = cur.fetchone()
        cur.execute(
            """
            INSERT INTO document_chunks (document_id, chunk_text, embedding, department, chunk_order)
            VALUES (%s, %s, %s::vector, %s, 0)
            """,
            (document_id, chunk_text, _format_vector(embedding), department),
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


def test_retrieve_relevant_chunks_filters_by_department(conn):
    close_vector = [1.0] * 1024
    titles = [
        _seed_chunk(conn, "sporting", "Sporting content.", close_vector),
        _seed_chunk(conn, "technical", "Technical content, embedding-wise closer.", close_vector),
    ]

    try:
        results = retrieve_relevant_chunks(conn, "sporting", close_vector, limit=5)

        assert len(results) == 1
        assert results[0]["chunk_text"] == "Sporting content."
    finally:
        _cleanup(titles)


def test_retrieve_relevant_chunks_orders_by_distance(conn):
    query_vector = [1.0] * 1024
    close_vector = [1.0] * 1024
    far_vector = [-1.0] * 1024
    titles = [
        _seed_chunk(conn, "sporting", "Closest chunk.", close_vector),
        _seed_chunk(conn, "sporting", "Farthest chunk.", far_vector),
    ]

    try:
        results = retrieve_relevant_chunks(conn, "sporting", query_vector, limit=5)

        assert results[0]["chunk_text"] == "Closest chunk."
        assert results[0]["distance"] < results[1]["distance"]
    finally:
        _cleanup(titles)


def test_retrieve_relevant_chunks_respects_limit(conn):
    vector = [1.0] * 1024
    titles = [_seed_chunk(conn, "sporting", f"Chunk {i}.", vector) for i in range(3)]

    try:
        results = retrieve_relevant_chunks(conn, "sporting", vector, limit=2)

        assert len(results) == 2
    finally:
        _cleanup(titles)


def test_retrieve_relevant_chunks_returns_empty_list_for_a_department_with_no_chunks(conn):
    results = retrieve_relevant_chunks(conn, "financial", [1.0] * 1024, limit=5)

    assert results == []


def test_retrieve_relevant_chunks_includes_the_source_document_title(conn):
    vector = [1.0] * 1024
    title = _seed_chunk(conn, "sporting", "Some content.", vector)

    try:
        results = retrieve_relevant_chunks(conn, "sporting", vector, limit=5)

        assert results[0]["document_title"] == title
    finally:
        _cleanup([title])
