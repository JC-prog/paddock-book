import psycopg

from src.modules.ingestion.embeddings import EmbeddedChunk


def title_exists(conn: psycopg.Connection, title: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM documents WHERE title = %s", (title,))
        return cur.fetchone() is not None


def write_document(
    conn: psycopg.Connection,
    title: str,
    department: str,
    chunks: list[EmbeddedChunk],
) -> None:
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (title) VALUES (%s) RETURNING id",
                (title,),
            )
            (document_id,) = cur.fetchone()

            for chunk in chunks:
                cur.execute(
                    """
                    INSERT INTO document_chunks
                        (document_id, chunk_text, embedding, department, chunk_order)
                    VALUES (%s, %s, %s::vector, %s, %s)
                    """,
                    (
                        document_id,
                        chunk.text,
                        _format_vector(chunk.embedding),
                        department,
                        chunk.order,
                    ),
                )


def _format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"
