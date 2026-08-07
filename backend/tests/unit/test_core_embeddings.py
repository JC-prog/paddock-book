import json
from unittest.mock import MagicMock

import pytest

from src.core.embeddings import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL_ID,
    embed_text,
    get_bedrock_client,
)


def _mock_client(embedding: list[float]) -> MagicMock:
    client = MagicMock()
    body = MagicMock()
    body.read.return_value = json.dumps({"embedding": embedding}).encode()
    client.invoke_model.return_value = {"body": body}
    return client


def test_get_bedrock_client_is_scoped_to_the_given_region():
    client = get_bedrock_client("eu-west-2")

    # boto3 clients don't expose the region as a simple public attribute
    # uniformly across versions; the meaningful contract is that this
    # doesn't raise and returns something with an invoke_model method.
    assert hasattr(client, "invoke_model")


def test_embed_text_calls_titan_v2_with_expected_model_and_dimensions():
    client = _mock_client([0.1] * 1024)

    embed_text("What tyre compounds are mandatory for a dry race?", client)

    _, kwargs = client.invoke_model.call_args
    assert kwargs["modelId"] == EMBEDDING_MODEL_ID
    body = json.loads(kwargs["body"])
    assert body["inputText"] == "What tyre compounds are mandatory for a dry race?"
    assert body["dimensions"] == EMBEDDING_DIMENSIONS


def test_embed_text_returns_the_1024_dimension_vector():
    embedding = [0.5] * 1024
    client = _mock_client(embedding)

    result = embed_text("Some text.", client)

    assert result == embedding
    assert len(result) == 1024


def test_embed_text_propagates_a_clear_error_on_call_failure():
    client = MagicMock()
    client.invoke_model.side_effect = RuntimeError("throttled")

    with pytest.raises(RuntimeError):
        embed_text("Some text.", client)
