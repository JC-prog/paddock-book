import psycopg

from src.core.embeddings import embed_text

RETRIEVAL_LIMIT = 5


def embed_question(text: str, client) -> list[float]:
    return embed_text(text, client)


def retrieve_relevant_chunks(
    conn: psycopg.Connection,
    department: str,
    query_embedding: list[float],
    limit: int = RETRIEVAL_LIMIT,
) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                document_chunks.chunk_text,
                documents.title,
                document_chunks.embedding <=> %s::vector AS distance
            FROM document_chunks
            JOIN documents ON documents.id = document_chunks.document_id
            WHERE document_chunks.department = %s
            ORDER BY document_chunks.embedding <=> %s::vector
            LIMIT %s
            """,
            (_format_vector(query_embedding), department, _format_vector(query_embedding), limit),
        )
        rows = cur.fetchall()

    return [
        {"chunk_text": row[0], "document_title": row[1], "distance": row[2]}
        for row in rows
    ]


def _format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"
