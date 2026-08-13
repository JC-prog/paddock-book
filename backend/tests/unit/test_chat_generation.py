import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.chat.generation import ChatProviderConfig, NO_RELEVANT_INFO_REPLY, generate_answer

pytestmark = pytest.mark.anyio


def _ollama_config(**overrides) -> ChatProviderConfig:
    defaults = {"provider": "ollama", "ollama_model": "llama3.2", "ollama_host": "http://localhost:11434"}
    defaults.update(overrides)
    return ChatProviderConfig(**defaults)


def _bedrock_config(**overrides) -> ChatProviderConfig:
    defaults = {
        "provider": "bedrock",
        "ollama_model": "llama3.2",
        "ollama_host": "http://localhost:11434",
        "bedrock_model": "anthropic.claude-3-5-sonnet-v2",
        "aws_region": "us-east-1",
    }
    defaults.update(overrides)
    return ChatProviderConfig(**defaults)


def _openai_compatible_config(**overrides) -> ChatProviderConfig:
    defaults = {
        "provider": "openai_compatible",
        "ollama_model": "llama3.2",
        "ollama_host": "http://localhost:11434",
        "openai_compatible_base_url": "https://api.openai.com/v1",
        "openai_compatible_api_key": "sk-test",
        "openai_compatible_model": "gpt-4o-mini",
    }
    defaults.update(overrides)
    return ChatProviderConfig(**defaults)


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

    result = [
        fragment
        async for fragment in generate_answer(
            "How many wheels?",
            chunks,
            provider_config=_ollama_config(),
            ollama_client_factory=client_factory,
        )
    ]

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
        provider_config=_ollama_config(),
        ollama_client_factory=client_factory,
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

    result = [
        fragment
        async for fragment in generate_answer(
            "A question?", chunks, provider_config=_ollama_config(), ollama_client_factory=client_factory
        )
    ]

    assert result == ["For", " dry", " conditions..."]


async def test_generate_answer_uses_the_configured_host():
    client_factory, _ = _mock_client_factory(["Hello"])
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Text."}]

    async for _ in generate_answer(
        "A question?",
        chunks,
        provider_config=_ollama_config(ollama_host="http://ollama.internal:11434"),
        ollama_client_factory=client_factory,
    ):
        pass

    client_factory.assert_called_once_with("http://ollama.internal:11434")


async def test_generate_answer_prompt_instructs_the_model_to_admit_when_context_does_not_answer():
    client_factory, client = _mock_client_factory(["An answer."])
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Cars must have four wheels."}]

    async for _ in generate_answer(
        "A question?", chunks, provider_config=_ollama_config(), ollama_client_factory=client_factory
    ):
        pass

    _, kwargs = client.chat.call_args
    messages = kwargs["messages"]
    system_message = next(m["content"] for m in messages if m["role"] == "system")
    assert NO_RELEVANT_INFO_REPLY in system_message


async def test_generate_answer_raises_for_an_unrecognized_provider():
    # Defense-in-depth: the admin API's Pydantic schema already restricts
    # active_provider to the 3 known values, but generation.py doesn't
    # trust that alone.
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Text."}]
    config = ChatProviderConfig(provider="not-a-real-provider", ollama_model="llama3.2", ollama_host="http://localhost:11434")

    with pytest.raises(NotImplementedError):
        async for _ in generate_answer("A question?", chunks, provider_config=config):
            pass


def _fake_converse_stream_events(fragments: list[str]):
    for fragment in fragments:
        yield {"contentBlockDelta": {"delta": {"text": fragment}}}


def _mock_bedrock_client_factory(fragments: list[str]):
    client = MagicMock()
    client.converse_stream.return_value = {"stream": _fake_converse_stream_events(fragments)}
    return MagicMock(return_value=client), client


async def test_generate_bedrock_calls_converse_stream_with_the_configured_model():
    client_factory, client = _mock_bedrock_client_factory(["Front", " wing"])
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Cars must have four wheels."}]

    result = [
        fragment
        async for fragment in generate_answer(
            "A question?",
            chunks,
            provider_config=_bedrock_config(),
            bedrock_client_factory=client_factory,
        )
    ]

    assert result == ["Front", " wing"]
    client.converse_stream.assert_called_once()
    _, kwargs = client.converse_stream.call_args
    assert kwargs["modelId"] == "anthropic.claude-3-5-sonnet-v2"


async def test_generate_bedrock_constructs_the_client_with_the_configured_region():
    client_factory, _ = _mock_bedrock_client_factory(["Hello"])
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Text."}]

    async for _ in generate_answer(
        "A question?",
        chunks,
        provider_config=_bedrock_config(aws_region="eu-west-1"),
        bedrock_client_factory=client_factory,
    ):
        pass

    client_factory.assert_called_once_with("eu-west-1")


async def test_generate_bedrock_includes_context_and_question_translated_into_converse_format():
    client_factory, client = _mock_bedrock_client_factory(["An answer."])
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Cars must have four wheels."}]

    async for _ in generate_answer(
        "How many wheels?", chunks, provider_config=_bedrock_config(), bedrock_client_factory=client_factory
    ):
        pass

    _, kwargs = client.converse_stream.call_args
    user_text = kwargs["messages"][0]["content"][0]["text"]
    system_text = kwargs["system"][0]["text"]
    assert "Cars must have four wheels." in user_text
    assert "How many wheels?" in user_text
    assert NO_RELEVANT_INFO_REPLY in system_text  # from the shared system prompt


async def test_generate_bedrock_dispatches_the_blocking_stream_iteration_via_a_background_thread():
    client_factory, _ = _mock_bedrock_client_factory(["Hello"])
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Text."}]

    with patch(
        "src.modules.chat.generation.asyncio.to_thread", wraps=asyncio.to_thread
    ) as mock_to_thread:
        async for _ in generate_answer(
            "A question?", chunks, provider_config=_bedrock_config(), bedrock_client_factory=client_factory
        ):
            pass

    mock_to_thread.assert_called_once()


def _fake_openai_chunk(content: str | None):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


async def _fake_openai_stream(fragments: list[str]):
    for fragment in fragments:
        yield _fake_openai_chunk(fragment)


def _mock_openai_client_factory(fragments: list[str]):
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=_fake_openai_stream(fragments))
    return MagicMock(return_value=client), client


async def test_generate_openai_compatible_calls_create_with_the_configured_model_and_streaming():
    client_factory, client = _mock_openai_client_factory(["Hello"])
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Cars must have four wheels."}]

    result = [
        fragment
        async for fragment in generate_answer(
            "How many wheels?",
            chunks,
            provider_config=_openai_compatible_config(),
            openai_client_factory=client_factory,
        )
    ]

    client.chat.completions.create.assert_called_once()
    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["stream"] is True
    assert result == ["Hello"]


async def test_generate_openai_compatible_constructs_the_client_with_base_url_and_api_key():
    client_factory, _ = _mock_openai_client_factory(["Hello"])
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Text."}]

    async for _ in generate_answer(
        "A question?",
        chunks,
        provider_config=_openai_compatible_config(
            openai_compatible_base_url="https://my-proxy.example/v1",
            openai_compatible_api_key="sk-secret",
        ),
        openai_client_factory=client_factory,
    ):
        pass

    client_factory.assert_called_once_with("https://my-proxy.example/v1", "sk-secret")


async def test_generate_openai_compatible_yields_streamed_fragments_in_order_and_skips_empty_deltas():
    client_factory, _ = _mock_openai_client_factory(["For", None, " dry", " conditions..."])
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Some regulation text."}]

    result = [
        fragment
        async for fragment in generate_answer(
            "A question?",
            chunks,
            provider_config=_openai_compatible_config(),
            openai_client_factory=client_factory,
        )
    ]

    assert result == ["For", " dry", " conditions..."]


async def test_generate_openai_compatible_includes_context_and_question_in_the_prompt():
    client_factory, client = _mock_openai_client_factory(["An answer."])
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Cars must have four wheels."}]

    async for _ in generate_answer(
        "How many wheels?",
        chunks,
        provider_config=_openai_compatible_config(),
        openai_client_factory=client_factory,
    ):
        pass

    _, kwargs = client.chat.completions.create.call_args
    messages = kwargs["messages"]
    joined = " ".join(m["content"] for m in messages)
    assert "Cars must have four wheels." in joined
    assert "How many wheels?" in joined
