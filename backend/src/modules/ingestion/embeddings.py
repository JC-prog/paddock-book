from dataclasses import dataclass

from src.core.embeddings import embed_text, get_bedrock_client
from src.modules.ingestion.chunker import Chunk


@dataclass
class EmbeddedChunk:
    text: str
    order: int
    embedding: list[float]


def embed_chunk(chunk: Chunk, client) -> EmbeddedChunk:
    embedding = embed_text(chunk.text, client)
    return EmbeddedChunk(text=chunk.text, order=chunk.order, embedding=embedding)
