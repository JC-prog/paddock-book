from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.chat.generation import generate_answer

pytestmark = pytest.mark.anyio


async def _fake_stream(fragments: list[str]):
    for fragment in fragments:
        yield {"message": {"content": fragment}}


def _mock_client_factory(fragments: list[str]):
    client = MagicMock()
    client.chat = AsyncMock(return_value=_fake_stream(fragments))
    return MagicMock(return_value=client), client


async def test_generate_answer_calls_ollama_with_expected_model_and_streaming():
    client_factory, client = _mock_client_factory(["Hello"])
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Cars must have four wheels."}]

    result = [fragment async for fragment in generate_answer(
        "How many wheels?", chunks, model="llama3.2", host="http://localhost:11434", client_factory=client_factory
    )]

    client.chat.assert_called_once()
    _, kwargs = client.chat.call_args
    assert kwargs["model"] == "llama3.2"
    assert kwargs["stream"] is True
    assert result == ["Hello"]


async def test_generate_answer_includes_retrieved_context_and_question_in_the_prompt():
    client_factory, client = _mock_client_factory(["An answer."])
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Cars must have four wheels."}]

    async for _ in generate_answer(
        "How many wheels are required?",
        chunks,
        model="llama3.2",
        host="http://localhost:11434",
        client_factory=client_factory,
    ):
        pass

    _, kwargs = client.chat.call_args
    messages = kwargs["messages"]
    joined = " ".join(m["content"] for m in messages)
    assert "Cars must have four wheels." in joined
    assert "Sporting Regs" in joined
    assert "How many wheels are required?" in joined


async def test_generate_answer_yields_streamed_fragments_in_order():
    client_factory, _ = _mock_client_factory(["For", " dry", " conditions..."])
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Some regulation text."}]

    result = [fragment async for fragment in generate_answer(
        "A question?", chunks, model="llama3.2", host="http://localhost:11434", client_factory=client_factory
    )]

    assert result == ["For", " dry", " conditions..."]


async def test_generate_answer_uses_the_configured_host():
    client_factory, _ = _mock_client_factory(["Hello"])
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Text."}]

    async for _ in generate_answer(
        "A question?",
        chunks,
        model="llama3.2",
        host="http://ollama.internal:11434",
        client_factory=client_factory,
    ):
        pass

    client_factory.assert_called_once_with("http://ollama.internal:11434")
