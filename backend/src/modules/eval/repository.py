import psycopg


def list_documents_with_chunks(conn: psycopg.Connection, department: str) -> dict[str, list[str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT documents.title, document_chunks.chunk_text
            FROM document_chunks
            JOIN documents ON documents.id = document_chunks.document_id
            WHERE document_chunks.department = %s
            ORDER BY documents.title, document_chunks.chunk_order
            """,
            (department,),
        )
        rows = cur.fetchall()

    result: dict[str, list[str]] = {}
    for title, chunk_text in rows:
        result.setdefault(title, []).append(chunk_text)
    return result
