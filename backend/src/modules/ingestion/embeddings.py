from dataclasses import dataclass

from src.core import embeddings as embeddings_module
from src.modules.ingestion.chunker import Chunk


@dataclass
class EmbeddedChunk:
    text: str
    order: int
    embedding: list[float]


def embed_chunk(chunk: Chunk, *, settings, embeddings=embeddings_module) -> EmbeddedChunk:
    embedding = embeddings.embed(
        chunk.text,
        provider=settings.embedding_provider,
        region_name=settings.aws_region,
        ollama_host=settings.ollama_host,
        ollama_model=settings.ollama_embedding_model,
    )
    return EmbeddedChunk(text=chunk.text, order=chunk.order, embedding=embedding)
