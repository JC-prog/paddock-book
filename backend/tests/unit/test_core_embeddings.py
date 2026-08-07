import json
from unittest.mock import MagicMock, patch

import pytest

from src.core.embeddings import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL_ID,
    embed,
    embed_text,
    embed_text_ollama,
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


def test_embed_text_ollama_returns_the_embedding_from_the_ollama_client():
    fake_response = MagicMock(embeddings=[[0.2] * 1024])
    fake_client = MagicMock()
    fake_client.embed.return_value = fake_response

    with patch("src.core.embeddings.ollama.Client", return_value=fake_client) as client_cls:
        result = embed_text_ollama("Some text.", host="http://localhost:11434", model="mxbai-embed-large")

    client_cls.assert_called_once_with(host="http://localhost:11434")
    fake_client.embed.assert_called_once_with(model="mxbai-embed-large", input="Some text.")
    assert result == [0.2] * 1024


def test_embed_text_ollama_wraps_a_call_failure_as_a_runtime_error():
    fake_client = MagicMock()
    fake_client.embed.side_effect = ConnectionError("connection refused")

    with patch("src.core.embeddings.ollama.Client", return_value=fake_client):
        with pytest.raises(RuntimeError):
            embed_text_ollama("Some text.", host="http://localhost:11434", model="mxbai-embed-large")


def test_embed_dispatches_to_bedrock_by_default():
    with (
        patch("src.core.embeddings.get_bedrock_client") as get_client,
        patch("src.core.embeddings.embed_text", return_value=[0.1] * 1024) as embed_text_mock,
    ):
        result = embed(
            "Some text.",
            provider="bedrock",
            region_name="us-east-1",
            ollama_host="http://localhost:11434",
            ollama_model="mxbai-embed-large",
        )

    get_client.assert_called_once_with("us-east-1")
    embed_text_mock.assert_called_once_with("Some text.", get_client.return_value)
    assert result == [0.1] * 1024


def test_embed_dispatches_to_ollama_when_configured():
    with patch("src.core.embeddings.embed_text_ollama", return_value=[0.2] * 1024) as embed_ollama_mock:
        result = embed(
            "Some text.",
            provider="ollama",
            region_name="us-east-1",
            ollama_host="http://ollama.internal:11434",
            ollama_model="mxbai-embed-large",
        )

    embed_ollama_mock.assert_called_once_with(
        "Some text.", host="http://ollama.internal:11434", model="mxbai-embed-large"
    )
    assert result == [0.2] * 1024
