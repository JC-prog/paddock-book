import json
from unittest.mock import MagicMock

import pytest

from src.modules.eval.judge import JudgingError, judge_answer


def _mock_client_factory(reply_content: str):
    client = MagicMock()
    client.chat.return_value = {"message": {"content": reply_content}}
    return MagicMock(return_value=client), client


def test_judge_answer_returns_true_for_a_correct_judgment():
    reply = json.dumps({"correct": True})
    client_factory, _ = _mock_client_factory(reply)

    result = judge_answer(
        "Four.", "The car must have four wheels.", model="llama3.2", host="http://localhost:11434", client_factory=client_factory
    )

    assert result is True


def test_judge_answer_returns_false_for_an_incorrect_judgment():
    reply = json.dumps({"correct": False})
    client_factory, _ = _mock_client_factory(reply)

    result = judge_answer(
        "Four.", "Six wheels.", model="llama3.2", host="http://localhost:11434", client_factory=client_factory
    )

    assert result is False


def test_judge_answer_raises_on_a_non_json_reply():
    client_factory, _ = _mock_client_factory("not json at all")

    with pytest.raises(JudgingError):
        judge_answer(
            "Four.", "Some answer.", model="llama3.2", host="http://localhost:11434", client_factory=client_factory
        )


def test_judge_answer_raises_when_the_reply_is_missing_the_correct_field():
    reply = json.dumps({"verdict": "yes"})
    client_factory, _ = _mock_client_factory(reply)

    with pytest.raises(JudgingError):
        judge_answer(
            "Four.", "Some answer.", model="llama3.2", host="http://localhost:11434", client_factory=client_factory
        )
