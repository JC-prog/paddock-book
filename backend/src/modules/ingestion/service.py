from src.core.config import Settings
from src.core.db import get_connection
from src.modules.ingestion import chunker as chunker_module
from src.modules.ingestion import embeddings as embeddings_module
from src.modules.ingestion import parser as parser_module
from src.modules.ingestion import repository as repository_module

DEPARTMENTS = {"sporting", "technical", "financial"}


def ingest(
    file_path: str,
    title: str,
    department: str,
    *,
    parser=parser_module,
    chunker=chunker_module,
    embeddings=embeddings_module,
    repository=repository_module,
    connection_factory=get_connection,
    settings_factory=Settings,
) -> None:
    if department not in DEPARTMENTS:
        raise ValueError(
            f"Unsupported department '{department}' — must be one of {sorted(DEPARTMENTS)}"
        )

    conn = connection_factory()
    try:
        if repository.title_exists(conn, title):
            raise ValueError(f"A document titled '{title}' already exists")

        text = parser.extract_text(file_path)
        chunks = chunker.chunk_text(text)

        settings = settings_factory()
        embedded_chunks = [
            embeddings.embed_chunk(chunk, settings=settings) for chunk in chunks
        ]

        repository.write_document(conn, title, department, embedded_chunks)
        conn.commit()
    finally:
        conn.close()
