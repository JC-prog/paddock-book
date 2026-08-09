from pathlib import Path
from unittest.mock import MagicMock, patch

from src.modules.eval.cli import main
from src.modules.eval.service import EvalSetNotFoundError, NoIngestedContentError


def test_generate_calls_generate_eval_set_and_prints_the_saved_path(capsys):
    with (
        patch("src.modules.eval.cli.get_connection", MagicMock()),
        patch(
            "src.modules.eval.cli.generate_eval_set",
            return_value=Path("data/eval/sets/sporting-x.json"),
        ) as mock_generate,
    ):
        exit_code = main(["generate", "--department", "sporting"])

    assert exit_code == 0
    mock_generate.assert_called_once()
    args, kwargs = mock_generate.call_args
    assert args[0] == "sporting"
    assert kwargs["questions_per_document"] == 3
    assert "data/eval/sets/sporting-x.json" in capsys.readouterr().out


def test_generate_passes_through_a_custom_questions_per_doc():
    with (
        patch("src.modules.eval.cli.get_connection", MagicMock()),
        patch(
            "src.modules.eval.cli.generate_eval_set",
            return_value=Path("data/eval/sets/sporting-x.json"),
        ) as mock_generate,
    ):
        main(["generate", "--department", "sporting", "--questions-per-doc", "5"])

    _, kwargs = mock_generate.call_args
    assert kwargs["questions_per_document"] == 5


def test_generate_reports_a_clean_error_and_exits_1_when_nothing_to_generate_from(capsys):
    with (
        patch("src.modules.eval.cli.get_connection", MagicMock()),
        patch(
            "src.modules.eval.cli.generate_eval_set", side_effect=NoIngestedContentError("no documents")
        ),
    ):
        exit_code = main(["generate", "--department", "financial"])

    assert exit_code == 1
    assert "no documents" in capsys.readouterr().err


def _write_report(tmp_path) -> Path:
    report_path = tmp_path / "sporting-x-y.md"
    report_path.write_text(
        "# Eval Report\n\n"
        "**Eval set**: data/eval/sets/sporting-x.json\n\n"
        "## Aggregate Metrics\n\n"
        "| Metric | Value |\n|---|---|\n"
        "| Hit Rate@5 | 1.0 |\n| MRR | 1.0 |\n| Answer accuracy | 1.0 (1/1 judged) |\n\n"
        "## Per-Question Results\n\n"
        "| # | Question | ... |\n"
    )
    return report_path


def test_run_calls_run_eval_and_prints_the_report_path_and_metrics(tmp_path, capsys):
    report_path = _write_report(tmp_path)
    with patch("src.modules.eval.cli.run_eval", return_value=report_path) as mock_run:
        exit_code = main(["run", "--eval-set", "data/eval/sets/sporting-x.json"])

    assert exit_code == 0
    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert args[0] == "data/eval/sets/sporting-x.json"
    out = capsys.readouterr().out
    assert str(report_path) in out
    assert "Hit Rate@5" in out


def test_run_reports_a_clean_error_and_exits_1_when_the_eval_set_is_missing(capsys):
    with patch("src.modules.eval.cli.run_eval", side_effect=EvalSetNotFoundError("not found: x.json")):
        exit_code = main(["run", "--eval-set", "x.json"])

    assert exit_code == 1
    assert "not found: x.json" in capsys.readouterr().err


def test_run_requires_the_eval_set_argument():
    try:
        main(["run"])
        assert False, "expected SystemExit from argparse"
    except SystemExit as exc:
        assert exc.code != 0
