import argparse
import sys

from tqdm import tqdm

from src.modules.download.service import count_documents_in_category, download_category


def _is_interactive() -> bool:
    return sys.stdout.isatty()


def _print_summary(result) -> None:
    print(
        f"Downloaded {len(result.downloaded)}, skipped {len(result.skipped)}, "
        f"failed {len(result.failed)}."
    )
    for failure in result.failed:
        print(f"  FAILED: {failure.source_url} ({failure.title or 'unknown title'}): {failure.reason}")


def _run_with_tty_progress(category_id: str, output_dir: str) -> int:
    count_bar = tqdm(desc="Counting documents", unit="page")
    try:
        total = count_documents_in_category(
            category_id, on_page_counted=lambda page: count_bar.update(1)
        )
    except Exception as exc:
        count_bar.close()
        print(f"Could not determine the document count: {exc}", file=sys.stderr)
        return 1
    count_bar.close()

    bar = tqdm(total=total, desc="Downloading", unit="doc")

    def on_progress(count: int) -> None:
        bar.n = count
        bar.refresh()

    def on_failure(failure) -> None:
        tqdm.write(f"FAILED: {failure.source_url} ({failure.title or 'unknown title'}): {failure.reason}")

    try:
        result = download_category(
            category_id, output_dir, on_progress=on_progress, on_failure=on_failure
        )
    except Exception as exc:
        bar.close()
        print(f"Download run could not proceed: {exc}", file=sys.stderr)
        return 1
    bar.close()

    _print_summary(result)
    return 0


def _run_with_plain_progress(category_id: str, output_dir: str) -> int:
    # Python fully buffers stdout (not line-buffers) when it isn't a TTY —
    # verified directly: a redirected run killed mid-flight left a
    # completely empty log file, since nothing had triggered a flush yet.
    # Without this, "readable output reflecting progress over time" would
    # only be true after the process exits normally, not while it runs —
    # exactly the case an operator redirecting a long run to check on
    # later (or tail live) actually cares about.
    sys.stdout.reconfigure(line_buffering=True)

    def on_page_counted(page: int) -> None:
        print(f"Counting documents... (page {page})")

    try:
        total = count_documents_in_category(category_id, on_page_counted=on_page_counted)
    except Exception as exc:
        print(f"Could not determine the document count: {exc}", file=sys.stderr)
        return 1

    print(f"Found {total} documents. Starting download.")

    last_reported_decile = 0

    def on_progress(count: int) -> None:
        nonlocal last_reported_decile
        if total == 0:
            return
        decile = (count * 10) // total
        if decile > last_reported_decile:
            last_reported_decile = decile
            percent = (count * 100) // total
            print(f"Progress: {count}/{total} ({percent}%)")

    def on_failure(failure) -> None:
        print(f"FAILED: {failure.source_url} ({failure.title or 'unknown title'}): {failure.reason}")

    try:
        result = download_category(
            category_id, output_dir, on_progress=on_progress, on_failure=on_failure
        )
    except Exception as exc:
        print(f"Download run could not proceed: {exc}", file=sys.stderr)
        return 1

    _print_summary(result)
    return 0


def main(argv: list[str] | None = None) -> int:
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
    args = parser.parse_args(argv)

    output_dir = args.output_dir or f"data/regulations/{args.category}"

    if _is_interactive():
        return _run_with_tty_progress(args.category, output_dir)

    return _run_with_plain_progress(args.category, output_dir)


if __name__ == "__main__":
    sys.exit(main())
