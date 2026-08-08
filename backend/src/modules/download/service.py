import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from src.modules.download import listing as listing_module
from src.modules.download import repository as repository_module
from src.modules.download.repository import ManifestEntry

CRAWL_DELAY_SECONDS = 10
CATEGORY_URL_TEMPLATE = "https://api.fia.com/regulation/category/{category_id}"
BASE_URL = "https://www.fia.com"


class RateLimiter:
    """Enforces a minimum gap between calls to wait(), per the source
    site's published crawl-delay (research.md — Rate limiting)."""

    def __init__(self, min_interval_seconds: float, *, clock=time.monotonic, sleep=time.sleep):
        self._min_interval = min_interval_seconds
        self._clock = clock
        self._sleep = sleep
        self._last_call_at: float | None = None

    def wait(self) -> None:
        now = self._clock()
        if self._last_call_at is not None:
            remaining = self._min_interval - (now - self._last_call_at)
            if remaining > 0:
                self._sleep(remaining)
        self._last_call_at = self._clock()


@dataclass
class DownloadFailure:
    source_url: str
    title: str | None
    reason: str


@dataclass
class DownloadRunResult:
    downloaded: list[ManifestEntry]
    skipped: list[str]
    failed: list[DownloadFailure]


def _default_fetch_page(url: str) -> str:
    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()
    return response.text


def _default_fetch_pdf(url: str) -> bytes:
    response = httpx.get(url, timeout=60, follow_redirects=True)
    response.raise_for_status()
    return response.content


def download_category(
    category_id: str,
    output_dir: Path,
    *,
    fetch_page=_default_fetch_page,
    fetch_pdf=_default_fetch_pdf,
    listing=listing_module,
    repository=repository_module,
    rate_limiter: RateLimiter | None = None,
    now=lambda: datetime.now(timezone.utc),
) -> DownloadRunResult:
    """Walks every listing page for a category and downloads every document
    found (User Story 1). Rate-limits every request to the source site,
    listing pages and PDFs alike, and continues past an individual
    document's failure rather than aborting the run (FR-005, FR-006)."""
    if rate_limiter is None:
        rate_limiter = RateLimiter(CRAWL_DELAY_SECONDS)

    manifest = repository.load_manifest(output_dir)
    downloaded: list[ManifestEntry] = []
    skipped: list[str] = []
    failed: list[DownloadFailure] = []

    page = 0
    while True:
        page_url = CATEGORY_URL_TEMPLATE.format(category_id=category_id)
        if page:
            page_url = f"{page_url}?page={page}"

        rate_limiter.wait()
        html = fetch_page(page_url)
        documents = listing.parse_listing_page(html, BASE_URL)

        for document in documents:
            if repository.is_downloaded(manifest, document.source_url):
                skipped.append(document.source_url)
                continue

            rate_limiter.wait()
            try:
                content = fetch_pdf(document.source_url)
                filename = repository.save_pdf(output_dir, document.source_url, content)
                entry = ManifestEntry(
                    title=document.title,
                    source_url=document.source_url,
                    section=document.section,
                    issue=document.issue,
                    published_date=(
                        document.published_date.isoformat() if document.published_date else None
                    ),
                    local_filename=filename,
                    downloaded_at=now().isoformat(),
                )
                repository.record_entry(output_dir, entry)
                downloaded.append(entry)
            except Exception as exc:
                failed.append(
                    DownloadFailure(source_url=document.source_url, title=document.title, reason=str(exc))
                )

        if not listing.has_next_page(html):
            break
        page += 1

    return DownloadRunResult(downloaded=downloaded, skipped=skipped, failed=failed)
