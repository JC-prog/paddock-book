import json
from unittest.mock import MagicMock

import pytest

from src.modules.eval.question_gen import QuestionGenerationError, generate_question


def _mock_client_factory(reply_content: str):
    client = MagicMock()
    client.chat.return_value = {"message": {"content": reply_content}}
    return MagicMock(return_value=client), client


def test_generate_question_parses_a_valid_structured_reply():
    reply = json.dumps({"question": "How many wheels?", "expected_answer": "Four."})
    client_factory, _ = _mock_client_factory(reply)

    question, expected_answer = generate_question(
        "A car must have four wheels.", model="llama3.2", host="http://localhost:11434", client_factory=client_factory
    )

    assert question == "How many wheels?"
    assert expected_answer == "Four."


def test_generate_question_raises_on_a_non_json_reply():
    client_factory, _ = _mock_client_factory("this is not json")

    with pytest.raises(QuestionGenerationError):
        generate_question(
            "Some chunk text.", model="llama3.2", host="http://localhost:11434", client_factory=client_factory
        )


def test_generate_question_raises_when_the_reply_is_missing_expected_fields():
    reply = json.dumps({"question": "How many wheels?"})
    client_factory, _ = _mock_client_factory(reply)

    with pytest.raises(QuestionGenerationError):
        generate_question(
            "Some chunk text.", model="llama3.2", host="http://localhost:11434", client_factory=client_factory
        )


def test_generate_question_uses_the_given_model_and_host():
    reply = json.dumps({"question": "Q", "expected_answer": "A"})
    client_factory, client = _mock_client_factory(reply)

    generate_question(
        "Chunk.", model="llama3.2", host="http://ollama.internal:11434", client_factory=client_factory
    )

    client_factory.assert_called_once_with("http://ollama.internal:11434")
    args, kwargs = client.chat.call_args
    assert kwargs["model"] == "llama3.2"
