import json
from unittest.mock import MagicMock

import pytest

from src.core.embeddings import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL_ID
from src.modules.ingestion.chunker import Chunk
from src.modules.ingestion.embeddings import embed_chunk


def _mock_client(embedding: list[float]) -> MagicMock:
    client = MagicMock()
    body = MagicMock()
    body.read.return_value = json.dumps({"embedding": embedding}).encode()
    client.invoke_model.return_value = {"body": body}
    return client


def test_embed_chunk_calls_titan_v2_with_expected_model_and_dimensions():
    client = _mock_client([0.1] * 1024)
    chunk = Chunk(text="Article 1: Cars must have four wheels.", order=0)

    embed_chunk(chunk, client)

    _, kwargs = client.invoke_model.call_args
    assert kwargs["modelId"] == EMBEDDING_MODEL_ID
    body = json.loads(kwargs["body"])
    assert body["inputText"] == chunk.text
    assert body["dimensions"] == EMBEDDING_DIMENSIONS


def test_embed_chunk_returns_embedded_chunk_with_1024_dimension_vector():
    embedding = [0.5] * 1024
    client = _mock_client(embedding)
    chunk = Chunk(text="Some regulation text.", order=3)

    result = embed_chunk(chunk, client)

    assert result.text == chunk.text
    assert result.order == chunk.order
    assert result.embedding == embedding
    assert len(result.embedding) == 1024


def test_embed_chunk_propagates_a_clear_error_on_call_failure():
    client = MagicMock()
    client.invoke_model.side_effect = RuntimeError("throttled")
    chunk = Chunk(text="Some regulation text.", order=0)

    with pytest.raises(RuntimeError):
        embed_chunk(chunk, client)
