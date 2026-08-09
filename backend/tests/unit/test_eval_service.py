from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.modules.chat import service as real_chat_service
from src.modules.eval import judge as real_judge
from src.modules.eval import question_gen as real_question_gen
from src.modules.eval import repository as real_repository
from src.modules.eval.judge import JudgingError
from src.modules.eval.question_gen import QuestionGenerationError
from src.modules.eval.schemas import EvalQuestion, EvalSet
from src.modules.eval.service import (
    EvalSetNotFoundError,
    NoIngestedContentError,
    generate_eval_set,
    run_eval,
)


def _settings_factory(**overrides):
    defaults = dict(ollama_model="llama3.2", ollama_host="http://localhost:11434")
    defaults.update(overrides)
    return MagicMock(return_value=MagicMock(**defaults))


async def _fake_answer(fragments: list[str]):
    for fragment in fragments:
        yield fragment


def _eval_set(tmp_path, *, questions=None):
    eval_set = EvalSet(
        department="sporting",
        generated_at=datetime.now(timezone.utc),
        questions_per_document=1,
        questions=questions
        or [
            EvalQuestion(
                question="How many wheels?", expected_answer="Four.", source_document_title="Doc A"
            )
        ],
    )
    return eval_set.save(base_dir=tmp_path)


def test_generate_eval_set_raises_when_the_department_has_no_ingested_documents():
    repository = MagicMock(spec=real_repository)
    repository.list_documents_with_chunks.return_value = {}
    question_gen = MagicMock(spec=real_question_gen)

    with pytest.raises(NoIngestedContentError):
        generate_eval_set(
            "financial",
            conn=MagicMock(),
            repository=repository,
            question_gen=question_gen,
            settings_factory=_settings_factory(),
        )

    question_gen.generate_question.assert_not_called()


def test_generate_eval_set_builds_one_question_per_sampled_chunk():
    repository = MagicMock(spec=real_repository)
    repository.list_documents_with_chunks.return_value = {"Doc A": ["chunk 1", "chunk 2"]}
    question_gen = MagicMock(spec=real_question_gen)
    question_gen.generate_question.side_effect = [
        ("Question 1?", "Answer 1."),
        ("Question 2?", "Answer 2."),
    ]

    path = generate_eval_set(
        "sporting",
        questions_per_document=2,
        conn=MagicMock(),
        repository=repository,
        question_gen=question_gen,
        settings_factory=_settings_factory(),
    )

    from src.modules.eval.schemas import EvalSet

    eval_set = EvalSet.load(path)
    assert eval_set.department == "sporting"
    assert eval_set.questions_per_document == 2
    assert len(eval_set.questions) == 2
    assert all(q.source_document_title == "Doc A" for q in eval_set.questions)
    assert {q.question for q in eval_set.questions} == {"Question 1?", "Question 2?"}

    path.unlink()


def test_generate_eval_set_skips_a_document_whose_generation_entirely_fails():
    repository = MagicMock(spec=real_repository)
    repository.list_documents_with_chunks.return_value = {
        "Bad Doc": ["chunk 1"],
        "Good Doc": ["chunk 1"],
    }
    question_gen = MagicMock(spec=real_question_gen)

    call_count = {"n": 0}

    def _generate(chunk_text, *, model, host):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise QuestionGenerationError("boom")
        return ("Good question?", "Good answer.")

    question_gen.generate_question.side_effect = _generate

    path = generate_eval_set(
        "sporting",
        questions_per_document=1,
        conn=MagicMock(),
        repository=repository,
        question_gen=question_gen,
        settings_factory=_settings_factory(),
    )

    from src.modules.eval.schemas import EvalSet

    eval_set = EvalSet.load(path)
    assert len(eval_set.questions) == 1
    assert eval_set.questions[0].source_document_title in {"Bad Doc", "Good Doc"}

    path.unlink()


def test_generate_eval_set_samples_evenly_across_a_documents_chunks():
    repository = MagicMock(spec=real_repository)
    chunks = [f"chunk {i}" for i in range(10)]
    repository.list_documents_with_chunks.return_value = {"Doc A": chunks}
    question_gen = MagicMock(spec=real_question_gen)
    question_gen.generate_question.side_effect = lambda chunk_text, **kwargs: (
        f"Q about {chunk_text}?",
        f"A about {chunk_text}.",
    )

    path = generate_eval_set(
        "sporting",
        questions_per_document=3,
        conn=MagicMock(),
        repository=repository,
        question_gen=question_gen,
        settings_factory=_settings_factory(),
    )

    sampled_chunks = [call.args[0] for call in question_gen.generate_question.call_args_list]
    assert len(sampled_chunks) == 3
    # Not clustered at the start: at least one sampled chunk should come
    # from later than the first third of the document.
    assert any(chunks.index(c) >= 3 for c in sampled_chunks)

    path.unlink()


def test_run_eval_raises_when_the_eval_set_file_does_not_exist(tmp_path):
    chat_service = MagicMock(spec=real_chat_service)
    judge = MagicMock(spec=real_judge)

    with pytest.raises(EvalSetNotFoundError):
        run_eval(
            tmp_path / "does-not-exist.json",
            connection_factory=MagicMock(),
            chat_service=chat_service,
            judge=judge,
            settings_factory=_settings_factory(),
        )

    chat_service.retrieve_context.assert_not_called()


def test_run_eval_calls_retrieval_and_generation_like_a_real_chat_request(tmp_path):
    eval_set_path = _eval_set(tmp_path)
    chat_service = MagicMock(spec=real_chat_service)
    chat_service.retrieve_context.return_value = [{"document_title": "Doc A", "chunk_text": "..."}]
    chat_service.generate_reply.side_effect = lambda *a, **kw: _fake_answer(["Four."])
    judge = MagicMock(spec=real_judge)
    judge.judge_answer.return_value = True
    connection_factory = MagicMock()

    path = run_eval(
        eval_set_path,
        connection_factory=connection_factory,
        chat_service=chat_service,
        judge=judge,
        settings_factory=_settings_factory(),
    )

    chat_service.retrieve_context.assert_called_once()
    args, kwargs = chat_service.retrieve_context.call_args
    assert args[0] == "How many wheels?"
    assert args[1] == "sporting"
    assert kwargs["conn"] == connection_factory.return_value

    chat_service.generate_reply.assert_called_once()
    gen_args, _ = chat_service.generate_reply.call_args
    assert gen_args[0] == "How many wheels?"
    assert gen_args[1] == [{"document_title": "Doc A", "chunk_text": "..."}]

    path.unlink()


def test_run_eval_marks_retrieved_true_with_the_correct_rank(tmp_path):
    eval_set_path = _eval_set(tmp_path)
    chat_service = MagicMock(spec=real_chat_service)
    chat_service.retrieve_context.return_value = [
        {"document_title": "Someone Else's Doc", "chunk_text": "..."},
        {"document_title": "Doc A", "chunk_text": "..."},
    ]
    chat_service.generate_reply.side_effect = lambda *a, **kw: _fake_answer(["Four."])
    judge = MagicMock(spec=real_judge)
    judge.judge_answer.return_value = True

    path = run_eval(
        eval_set_path,
        connection_factory=MagicMock(),
        chat_service=chat_service,
        judge=judge,
        settings_factory=_settings_factory(),
    )

    row = next(line for line in path.read_text().splitlines() if "How many wheels?" in line)
    assert "✅" in row
    assert row.split("|")[5].strip() == "2"

    path.unlink()


def test_run_eval_marks_retrieved_false_when_source_document_is_missing(tmp_path):
    eval_set_path = _eval_set(tmp_path)
    chat_service = MagicMock(spec=real_chat_service)
    chat_service.retrieve_context.return_value = [{"document_title": "Some Other Doc", "chunk_text": "..."}]
    chat_service.generate_reply.side_effect = lambda *a, **kw: _fake_answer(["An answer."])
    judge = MagicMock(spec=real_judge)
    judge.judge_answer.return_value = False

    path = run_eval(
        eval_set_path,
        connection_factory=MagicMock(),
        chat_service=chat_service,
        judge=judge,
        settings_factory=_settings_factory(),
    )

    content = path.read_text()
    assert "❌" in content

    path.unlink()


def test_run_eval_records_failure_and_continues_when_retrieval_raises(tmp_path):
    eval_set_path = _eval_set(tmp_path)
    chat_service = MagicMock(spec=real_chat_service)
    chat_service.retrieve_context.side_effect = RuntimeError("db unreachable")
    judge = MagicMock(spec=real_judge)

    path = run_eval(
        eval_set_path,
        connection_factory=MagicMock(),
        chat_service=chat_service,
        judge=judge,
        settings_factory=_settings_factory(),
    )

    content = path.read_text()
    assert "db unreachable" in content
    chat_service.generate_reply.assert_not_called()
    judge.judge_answer.assert_not_called()

    path.unlink()


def test_run_eval_records_failure_and_continues_when_generation_raises(tmp_path):
    eval_set_path = _eval_set(tmp_path)
    chat_service = MagicMock(spec=real_chat_service)
    chat_service.retrieve_context.return_value = [{"document_title": "Doc A", "chunk_text": "..."}]

    async def _raise_gen(*a, **kw):
        raise RuntimeError("ollama unreachable")
        yield  # pragma: no cover - makes this an async generator function

    chat_service.generate_reply.side_effect = _raise_gen
    judge = MagicMock(spec=real_judge)

    path = run_eval(
        eval_set_path,
        connection_factory=MagicMock(),
        chat_service=chat_service,
        judge=judge,
        settings_factory=_settings_factory(),
    )

    content = path.read_text()
    assert "ollama unreachable" in content
    judge.judge_answer.assert_not_called()

    path.unlink()


def test_run_eval_records_failure_and_continues_when_judging_raises(tmp_path):
    eval_set_path = _eval_set(tmp_path)
    chat_service = MagicMock(spec=real_chat_service)
    chat_service.retrieve_context.return_value = [{"document_title": "Doc A", "chunk_text": "..."}]
    chat_service.generate_reply.side_effect = lambda *a, **kw: _fake_answer(["Four."])
    judge = MagicMock(spec=real_judge)
    judge.judge_answer.side_effect = JudgingError("bad json")

    path = run_eval(
        eval_set_path,
        connection_factory=MagicMock(),
        chat_service=chat_service,
        judge=judge,
        settings_factory=_settings_factory(),
    )

    content = path.read_text()
    assert "bad json" in content

    path.unlink()


def test_run_eval_computes_aggregate_metrics_excluding_failed_judgments(tmp_path):
    questions = [
        EvalQuestion(question="Q1", expected_answer="A1", source_document_title="Doc A"),
        EvalQuestion(question="Q2", expected_answer="A2", source_document_title="Doc A"),
        EvalQuestion(question="Q3", expected_answer="A3", source_document_title="Doc A"),
    ]
    eval_set_path = _eval_set(tmp_path, questions=questions)

    chat_service = MagicMock(spec=real_chat_service)
    chat_service.retrieve_context.return_value = [{"document_title": "Doc A", "chunk_text": "..."}]
    chat_service.generate_reply.side_effect = lambda *a, **kw: _fake_answer(["An answer."])

    judge = MagicMock(spec=real_judge)
    judge.judge_answer.side_effect = [True, False, JudgingError("unparseable")]

    path = run_eval(
        eval_set_path,
        connection_factory=MagicMock(),
        chat_service=chat_service,
        judge=judge,
        settings_factory=_settings_factory(),
    )

    saved = path.read_text()
    assert "3/3 judged" not in saved  # one question's judgment failed
    assert "2/3 judged" in saved

    path.unlink()


def test_run_eval_saves_a_report_and_returns_its_path(tmp_path):
    eval_set_path = _eval_set(tmp_path)
    chat_service = MagicMock(spec=real_chat_service)
    chat_service.retrieve_context.return_value = [{"document_title": "Doc A", "chunk_text": "..."}]
    chat_service.generate_reply.side_effect = lambda *a, **kw: _fake_answer(["Four."])
    judge = MagicMock(spec=real_judge)
    judge.judge_answer.return_value = True

    path = run_eval(
        eval_set_path,
        connection_factory=MagicMock(),
        chat_service=chat_service,
        judge=judge,
        settings_factory=_settings_factory(),
    )

    assert path.exists()
    assert path.suffix == ".md"

    path.unlink()
