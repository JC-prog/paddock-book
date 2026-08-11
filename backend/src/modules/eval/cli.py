import argparse
import sys
from pathlib import Path

from src.core.db import get_connection
from src.modules.eval.service import (
    EvalSetNotFoundError,
    NoIngestedContentError,
    generate_eval_set,
    run_eval,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.modules.eval.cli",
        description="Generate and run fixed RAG evaluation sets against currently-ingested content.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    generate_parser = subparsers.add_parser("generate", help="Synthesize a fixed eval set from ingested content")
    generate_parser.add_argument("--department", required=True, help="One of: sporting, technical, financial")
    generate_parser.add_argument(
        "--questions-per-doc",
        type=int,
        default=3,
        help="How many questions to generate per ingested document (default: 3)",
    )

    run_parser = subparsers.add_parser("run", help="Score a previously generated eval set")
    run_parser.add_argument(
        "--eval-set", required=True, help="Path to a .json file produced by the generate subcommand"
    )

    return parser


def _run_generate(args: argparse.Namespace) -> int:
    conn = get_connection()
    try:
        path = generate_eval_set(args.department, questions_per_document=args.questions_per_doc, conn=conn)
    except NoIngestedContentError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        conn.close()

    print(f"Eval set saved to {path}")
    return 0


def _extract_aggregate_metrics_section(markdown: str) -> str:
    start = markdown.index("## Aggregate Metrics")
    end = markdown.index("## Per-Question Results")
    return markdown[start:end].strip()


def _run_run(args: argparse.Namespace) -> int:
    try:
        path = run_eval(args.eval_set)
    except EvalSetNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Report saved to {path}")
    print()
    print(_extract_aggregate_metrics_section(Path(path).read_text()))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.action == "generate":
        return _run_generate(args)
    if args.action == "run":
        return _run_run(args)

    parser.error(f"unknown action {args.action!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
