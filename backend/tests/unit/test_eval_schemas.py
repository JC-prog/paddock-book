from datetime import datetime, timezone

from src.modules.eval.schemas import EvalQuestion, EvalReport, EvalResult, EvalSet


def _question(title: str = "Reg Doc") -> EvalQuestion:
    return EvalQuestion(
        question="How many wheels must a car have?",
        expected_answer="Exactly four.",
        source_document_title=title,
    )


def test_eval_set_save_writes_under_the_given_base_dir(tmp_path):
    eval_set = EvalSet(
        department="sporting",
        generated_at=datetime.now(timezone.utc),
        questions_per_document=3,
        questions=[_question()],
    )

    path = eval_set.save(base_dir=tmp_path)

    assert path.exists()
    assert path.parent == tmp_path
    assert path.name.startswith("sporting-")
    assert path.suffix == ".json"


def test_eval_set_save_then_load_round_trips_exactly(tmp_path):
    eval_set = EvalSet(
        department="technical",
        generated_at=datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc),
        questions_per_document=2,
        questions=[_question("Doc A"), _question("Doc B")],
    )

    path = eval_set.save(base_dir=tmp_path)
    loaded = EvalSet.load(path)

    assert loaded.department == "technical"
    assert loaded.questions_per_document == 2
    assert loaded.generated_at == eval_set.generated_at
    assert [q.source_document_title for q in loaded.questions] == ["Doc A", "Doc B"]
    assert loaded.questions[0].question == eval_set.questions[0].question
    assert loaded.questions[0].expected_answer == eval_set.questions[0].expected_answer


def test_eval_set_save_twice_produces_two_distinct_files(tmp_path):
    eval_set = EvalSet(
        department="sporting",
        generated_at=datetime.now(timezone.utc),
        questions_per_document=1,
        questions=[_question()],
    )

    first_path = eval_set.save(base_dir=tmp_path)
    second_path = eval_set.save(base_dir=tmp_path)

    assert first_path != second_path
    assert first_path.exists()
    assert second_path.exists()


def _result(**overrides) -> EvalResult:
    defaults = dict(
        question="How many wheels?",
        source_document_title="Reg Doc",
        retrieved=True,
        rank=1,
        generated_answer="Four.",
        judged_correct=True,
        failure_reason=None,
    )
    defaults.update(overrides)
    return EvalResult(**defaults)


def _report(**overrides) -> EvalReport:
    defaults = dict(
        eval_set_path="data/eval/sets/sporting-20260809-120000.json",
        run_at=datetime(2026, 8, 9, 12, 5, 0, tzinfo=timezone.utc),
        k=5,
        results=[_result()],
        hit_rate=1.0,
        mrr=1.0,
        answer_accuracy=1.0,
        judged_count=1,
    )
    defaults.update(overrides)
    return EvalReport(**defaults)


def test_report_markdown_includes_the_header_block():
    report = _report()

    markdown = report.to_markdown()

    assert "data/eval/sets/sporting-20260809-120000.json" in markdown
    assert "2026-08-09T12:05:00" in markdown
    assert "5" in markdown


def test_report_markdown_includes_aggregate_metrics():
    report = _report(hit_rate=0.86, mrr=0.71, answer_accuracy=0.9, judged_count=18, results=[_result()] * 20)

    markdown = report.to_markdown()

    assert "0.86" in markdown
    assert "0.71" in markdown
    assert "0.9" in markdown
    assert "18/20" in markdown


def test_report_markdown_shows_the_generated_answer_for_each_question():
    report = _report(results=[_result(generated_answer="The wheels must be made of magnesium alloy.")])

    markdown = report.to_markdown()

    assert "The wheels must be made of magnesium alloy." in markdown


def test_report_markdown_escapes_pipe_characters_in_the_generated_answer():
    report = _report(results=[_result(generated_answer="It's four | not six.")])

    markdown = report.to_markdown()

    assert "four \\| not six" in markdown


def test_report_markdown_shows_no_rank_when_not_retrieved():
    report = _report(results=[_result(retrieved=False, rank=None)])

    markdown = report.to_markdown()

    lines = [line for line in markdown.splitlines() if "How many wheels?" in line]
    assert len(lines) == 1
    assert "❌" in lines[0]


def test_report_markdown_shows_failure_reason_and_no_correct_mark_when_judging_failed():
    report = _report(
        results=[
            _result(
                judged_correct=None,
                generated_answer=None,
                failure_reason="judging: response was not valid JSON",
            )
        ]
    )

    markdown = report.to_markdown()

    lines = [line for line in markdown.splitlines() if "How many wheels?" in line]
    assert len(lines) == 1
    row = lines[0]
    assert "judging: response was not valid JSON" in row
    # Distinct from an actual incorrect judgment: no ❌ standing in for "judged and wrong"
    assert "✅" not in row.split("|")[7]
    assert "❌" not in row.split("|")[7]
