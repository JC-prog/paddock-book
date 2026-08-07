import os
import uuid
from unittest.mock import MagicMock

import psycopg

from src.modules.ingestion.embeddings import EmbeddedChunk
from src.modules.ingestion.service import ingest


def _connect() -> psycopg.Connection:
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql://paddockbook:paddockbook@localhost:5432/paddockbook",
    )
    return psycopg.connect(dsn)


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


def test_ingest_persists_the_document_and_chunks_visibly_to_a_new_connection():
    """Runs the real ingest() against a real DB (parser/embeddings mocked to
    avoid needing a real PDF or a live Bedrock/Ollama call) and checks the
    write via a *separate* connection — the only way to catch a missing
    conn.commit() leaving everything rolled back on close."""
    title = f"Integration Test Ingest {uuid.uuid4()}"
    parser = MagicMock()
    parser.extract_text.return_value = "Some regulation text about tyre compounds."
    embeddings = MagicMock()
    embeddings.embed_chunk.side_effect = lambda chunk, **kwargs: EmbeddedChunk(
        text=chunk.text, order=chunk.order, embedding=[0.1] * 1024
    )

    try:
        ingest("unused.pdf", title, "sporting", parser=parser, embeddings=embeddings)

        with _connect() as check_conn:
            with check_conn.cursor() as cur:
                cur.execute("SELECT id FROM documents WHERE title = %s", (title,))
                document_row = cur.fetchone()
                assert document_row is not None

                cur.execute(
                    "SELECT count(*) FROM document_chunks WHERE document_id = %s",
                    (document_row[0],),
                )
                assert cur.fetchone()[0] == 1
    finally:
        _cleanup(title)
