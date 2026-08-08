from unittest.mock import MagicMock

import pytest

from src.core import embeddings as real_embeddings
from src.modules.ingestion.chunker import Chunk
from src.modules.ingestion.embeddings import embed_chunk


def _settings(**overrides):
    defaults = {
        "embedding_provider": "bedrock",
        "aws_region": "us-east-1",
        "ollama_host": "http://localhost:11434",
        "ollama_embedding_model": "mxbai-embed-large",
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def test_embed_chunk_delegates_to_the_shared_embedding_dispatcher_with_settings():
    embeddings = MagicMock(spec=real_embeddings)
    embeddings.embed.return_value = [0.1] * 1024
    chunk = Chunk(text="Article 1: Cars must have four wheels.", order=0)

    embed_chunk(chunk, settings=_settings(), embeddings=embeddings)

    embeddings.embed.assert_called_once_with(
        chunk.text,
        provider="bedrock",
        region_name="us-east-1",
        ollama_host="http://localhost:11434",
        ollama_model="mxbai-embed-large",
    )


def test_embed_chunk_returns_embedded_chunk_with_the_dispatched_vector():
    embedding = [0.5] * 1024
    embeddings = MagicMock(spec=real_embeddings)
    embeddings.embed.return_value = embedding
    chunk = Chunk(text="Some regulation text.", order=3)

    result = embed_chunk(chunk, settings=_settings(), embeddings=embeddings)

    assert result.text == chunk.text
    assert result.order == chunk.order
    assert result.embedding == embedding
    assert len(result.embedding) == 1024


def test_embed_chunk_propagates_a_clear_error_on_dispatch_failure():
    embeddings = MagicMock(spec=real_embeddings)
    embeddings.embed.side_effect = RuntimeError("bedrock unavailable")
    chunk = Chunk(text="Some regulation text.", order=0)

    with pytest.raises(RuntimeError):
        embed_chunk(chunk, settings=_settings(), embeddings=embeddings)
