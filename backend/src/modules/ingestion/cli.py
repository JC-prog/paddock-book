import argparse
import sys

from src.modules.ingestion.service import DEPARTMENTS, ingest


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.modules.ingestion.cli",
        description="Ingest a PDF regulation document into the searchable knowledge base.",
    )
    parser.add_argument("--file", required=True, help="Path to the PDF to ingest")
    parser.add_argument(
        "--title", required=True, help="Document title — also its identity for duplicate detection"
    )
    parser.add_argument(
        "--department",
        required=True,
        help=f"One of: {', '.join(sorted(DEPARTMENTS))}",
    )
    args = parser.parse_args()

    try:
        ingest(args.file, args.title, args.department)
    except Exception as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1

    print(f"Ingested '{args.title}' successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
