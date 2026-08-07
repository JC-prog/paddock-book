from unittest.mock import MagicMock

import pytest

from src.core import embeddings as real_embeddings
from src.modules.chat import generation as real_generation
from src.modules.chat import retrieval as real_retrieval
from src.modules.chat.generation import NO_RELEVANT_INFO_REPLY
from src.modules.chat.service import generate_reply, retrieve_context

pytestmark = pytest.mark.anyio


def _settings_factory(**overrides):
    defaults = {"aws_region": "us-east-1", "ollama_model": "llama3.2", "ollama_host": "http://localhost:11434"}
    defaults.update(overrides)
    return MagicMock(return_value=MagicMock(**defaults))


def _retrieval_collaborators(chunks=None):
    if chunks is None:
        chunks = [{"document_title": "Sporting Regs", "chunk_text": "Cars must have four wheels."}]

    embeddings = MagicMock(spec=real_embeddings)
    embeddings.get_bedrock_client.return_value = MagicMock()

    retrieval = MagicMock(spec=real_retrieval)
    retrieval.embed_question.return_value = [0.1] * 1024
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

    collaborators["retrieval"].embed_question.assert_called_once()
    collaborators["retrieval"].retrieve_relevant_chunks.assert_called_once_with(
        collaborators["conn"], "sporting", collaborators["retrieval"].embed_question.return_value
    )
    assert result == collaborators["retrieval"].retrieve_relevant_chunks.return_value


def test_retrieve_context_uses_the_requesters_department():
    collaborators = _retrieval_collaborators()

    retrieve_context("A question?", "technical", **collaborators)

    args, _ = collaborators["retrieval"].retrieve_relevant_chunks.call_args
    assert args[1] == "technical"


def test_retrieve_context_closes_the_connection_even_on_failure():
    collaborators = _retrieval_collaborators()
    collaborators["retrieval"].embed_question.side_effect = RuntimeError("Bedrock unavailable")

    with pytest.raises(RuntimeError):
        retrieve_context("A question?", "sporting", **collaborators)

    collaborators["conn"].close.assert_called_once()


def test_retrieve_context_closes_the_connection_on_success():
    collaborators = _retrieval_collaborators()

    retrieve_context("A question?", "sporting", **collaborators)

    collaborators["conn"].close.assert_called_once()


async def test_generate_reply_yields_the_generation_module_output():
    chunks = [{"document_title": "Sporting Regs", "chunk_text": "Cars must have four wheels."}]
    generation = MagicMock(spec=real_generation)

    async def fake_generate_answer(question, given_chunks, *, model, host):
        assert question == "How many wheels?"
        assert given_chunks == chunks
        yield "Four"
        yield " wheels."

    generation.generate_answer = fake_generate_answer

    result = [
        fragment
        async for fragment in generate_reply(
            "How many wheels?", chunks, settings_factory=_settings_factory(), generation=generation
        )
    ]

    assert result == ["Four", " wheels."]


async def test_generate_reply_returns_the_no_relevant_info_reply_without_calling_generation_when_no_chunks_were_retrieved():
    generation = MagicMock(spec=real_generation)

    result = [
        fragment
        async for fragment in generate_reply(
            "An unrelated question?", [], settings_factory=_settings_factory(), generation=generation
        )
    ]

    generation.generate_answer.assert_not_called()
    assert result == [NO_RELEVANT_INFO_REPLY]
