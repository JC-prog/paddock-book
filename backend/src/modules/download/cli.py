import argparse
import sys

from src.modules.download.service import download_category


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.modules.download.cli",
        description="Download FIA regulation PDFs for a category, saving each with its metadata.",
    )
    parser.add_argument("--category", required=True, help="FIA regulation category ID, e.g. 110")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Where PDFs and manifest.json are stored (default: data/regulations/<category>)",
    )
    args = parser.parse_args()

    output_dir = args.output_dir or f"data/regulations/{args.category}"

    try:
        result = download_category(args.category, output_dir)
    except Exception as exc:
        print(f"Download run could not proceed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Downloaded {len(result.downloaded)}, skipped {len(result.skipped)}, "
        f"failed {len(result.failed)}."
    )
    for failure in result.failed:
        print(f"  FAILED: {failure.source_url} ({failure.title or 'unknown title'}): {failure.reason}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
