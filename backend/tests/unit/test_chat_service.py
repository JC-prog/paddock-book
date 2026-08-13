from unittest.mock import MagicMock

import psycopg
import pytest

from src.core import embeddings as real_embeddings
from src.modules.admin import repository as real_admin_repository
from src.modules.chat import generation as real_generation
from src.modules.chat import retrieval as real_retrieval
from src.modules.chat.generation import NO_RELEVANT_INFO_REPLY, ChatProviderConfig
from src.modules.chat.service import generate_reply, resolve_provider_config, retrieve_context

pytestmark = pytest.mark.anyio


def _settings_factory(**overrides):
    defaults = {
        "aws_region": "us-east-1",
        "ollama_model": "llama3.2",
        "ollama_host": "http://localhost:11434",
        "embedding_provider": "bedrock",
        "ollama_embedding_model": "mxbai-embed-large",
    }
    defaults.update(overrides)
    return MagicMock(return_value=MagicMock(**defaults))


def _retrieval_collaborators(chunks=None):
    if chunks is None:
        chunks = [{"document_title": "Sporting Regs", "chunk_text": "Cars must have four wheels."}]

    embeddings = MagicMock(spec=real_embeddings)
    embeddings.embed.return_value = [0.1] * 1024

    retrieval = MagicMock(spec=real_retrieval)
    retrieval.retrieve_relevant_chunks.return_value = chunks

    return {
        "conn": MagicMock(),
        "settings_factory": _settings_factory(),
        "embeddings": embeddings,
        "retrieval": retrieval,
    }


def test_retrieve_context_embeds_the_question_and_retrieves_department_scoped_chunks():
    collaborators = _retrieval_collaborators()

    result = retrieve_context("How many wheels?", "sporting", **collaborators)

    collaborators["embeddings"].embed.assert_called_once_with(
        "How many wheels?",
        provider="bedrock",
        region_name="us-east-1",
        ollama_host="http://localhost:11434",
        ollama_model="mxbai-embed-large",
    )
    collaborators["retrieval"].retrieve_relevant_chunks.assert_called_once_with(
        collaborators["conn"], "sporting", collaborators["embeddings"].embed.return_value
    )
    assert result == collaborators["retrieval"].retrieve_relevant_chunks.return_value


def test_retrieve_context_uses_the_requesters_department():
    collaborators = _retrieval_collaborators()

    retrieve_context("A question?", "technical", **collaborators)

    args, _ = collaborators["retrieval"].retrieve_relevant_chunks.call_args
    assert args[1] == "technical"


def test_retrieve_context_closes_the_connection_even_on_failure():
    collaborators = _retrieval_collaborators()
    collaborators["embeddings"].embed.side_effect = RuntimeError("Bedrock unavailable")

    with pytest.raises(RuntimeError):
        retrieve_context("A question?", "sporting", **collaborators)

    collaborators["conn"].close.assert_called_once()


def test_retrieve_context_wraps_a_database_error_as_a_runtime_error():
    collaborators = _retrieval_collaborators()
    collaborators["retrieval"].retrieve_relevant_chunks.side_effect = psycopg.OperationalError(
        "connection lost"
    )

    with pytest.raises(RuntimeError):
        retrieve_context("A question?", "sporting", **collaborators)

    collaborators["conn"].close.assert_called_once()


def test_retrieve_context_closes_the_connection_on_success():
    collaborators = _retrieval_collaborators()

    retrieve_context("A question?", "sporting", **collaborators)

    collaborators["conn"].close.assert_called_once()


def test_resolve_provider_config_falls_back_to_settings_when_no_row_exists():
    admin_repository = MagicMock(spec=real_admin_repository)
    admin_repository.get_chat_provider_settings.return_value = None

    result = resolve_provider_config(
        conn=MagicMock(), admin_repository=admin_repository, settings_factory=_settings_factory()
    )

    assert result == ChatProviderConfig(
        provider="ollama",
        ollama_model="llama3.2",
        ollama_host="http://localhost:11434",
        aws_region="us-east-1",
    )


def test_resolve_provider_config_uses_the_stored_row_when_present():
    admin_repository = MagicMock(spec=real_admin_repository)
    admin_repository.get_chat_provider_settings.return_value = {
        "active_provider": "openai_compatible",
        "ollama_model_override": None,
        "bedrock_model": None,
        "openai_compatible_base_url": "https://api.openai.com/v1",
        "openai_compatible_api_key": "sk-test",
        "openai_compatible_model": "gpt-4o-mini",
        "updated_at": "2026-08-12T00:00:00Z",
    }

    result = resolve_provider_config(
        conn=MagicMock(), admin_repository=admin_repository, settings_factory=_settings_factory()
    )

    assert result.provider == "openai_compatible"
    assert result.openai_compatible_base_url == "https://api.openai.com/v1"
    assert result.openai_compatible_api_key == "sk-test"
    assert result.openai_compatible_model == "gpt-4o-mini"


def test_resolve_provider_config_falls_back_to_the_default_ollama_model_when_no_override_saved():
    admin_repository = MagicMock(spec=real_admin_repository)
    admin_repository.get_chat_provider_settings.return_value = {
        "active_provider": "ollama",
        "ollama_model_override": None,
        "bedrock_model": None,
        "openai_compatible_base_url": None,
        "openai_compatible_api_key": None,
        "openai_compatible_model": None,
        "updated_at": "2026-08-12T00:00:00Z",
    }

    result = resolve_provider_config(
        conn=MagicMock(), admin_repository=admin_repository, settings_factory=_settings_factory()
    )

    assert result.ollama_model == "llama3.2"


def test_resolve_provider_config_uses_the_saved_ollama_model_override_when_present():
    admin_repository = MagicMock(spec=real_admin_repository)
    admin_repository.get_chat_provider_settings.return_value = {
        "active_provider": "ollama",
        "ollama_model_override": "llama3.3",
        "bedrock_model": None,
        "openai_compatible_base_url": None,
        "openai_compatible_api_key": None,
        "openai_compatible_model": None,
        "updated_at": "2026-08-12T00:00:00Z",
    }

    result = resolve_provider_config(
        conn=MagicMock(), admin_repository=admin_repository, settings_factory=_settings_factory()
    )

    assert result.ollama_model == "llama3.3"


def _provider_config(**overrides) -> ChatProviderConfig:
    defaults = {"provider": "ollama", "ollama_model": "llama3.2", "ollama_host": "http://localhost:11434"}
    defaults.update(overrides)
    return ChatProviderConfig(**defaults)


async def test_generate_reply_yields_the_generation_module_output():
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Cars must have four wheels."}]
    generation = MagicMock(spec=real_generation)
    provider_config = _provider_config()

    async def fake_generate_answer(question, given_chunks, *, provider_config):
        assert question == "How many wheels?"
        assert given_chunks == chunks
        yield "Four"
        yield " wheels."

    generation.generate_answer = fake_generate_answer

    result = [
        fragment
        async for fragment in generate_reply(
            "How many wheels?", chunks, provider_config=provider_config, generation=generation
        )
    ]

    assert result == ["Four", " wheels."]


async def test_generate_reply_calls_generation_with_the_given_provider_config():
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Cars must have four wheels."}]
    generation = MagicMock(spec=real_generation)

    async def fake_generate_answer(question, given_chunks, *, provider_config):
        yield "ok"

    generation.generate_answer = fake_generate_answer
    provider_config = _provider_config(provider="bedrock", bedrock_model="anthropic.claude-3-5-sonnet-v2")

    async for _ in generate_reply(
        "A question?", chunks, provider_config=provider_config, generation=generation
    ):
        pass


async def test_generate_reply_returns_the_no_relevant_info_reply_without_calling_generation_when_no_chunks_were_retrieved():
    generation = MagicMock(spec=real_generation)

    result = [
        fragment
        async for fragment in generate_reply(
            "An unrelated question?", [], provider_config=_provider_config(), generation=generation
        )
    ]

    generation.generate_answer.assert_not_called()
    assert result == [NO_RELEVANT_INFO_REPLY]
