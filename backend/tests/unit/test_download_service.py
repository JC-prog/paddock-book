import datetime
from unittest.mock import MagicMock, call

from src.modules.download import listing as real_listing
from src.modules.download import repository as real_repository
from src.modules.download.listing import ListedDocument
from src.modules.download.service import CATEGORY_URL_TEMPLATE, RateLimiter, download_category


def _doc(source_url, title="Doc", **overrides):
    defaults = dict(title=title, section=None, issue=None, published_date=None)
    defaults.update(overrides)
    return ListedDocument(source_url=source_url, **defaults)


class FakeClock:
    def __init__(self, start: float):
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


def test_rate_limiter_does_not_wait_before_the_first_call():
    clock = FakeClock(start=1000.0)
    sleeps: list[float] = []
    limiter = RateLimiter(10, clock=clock, sleep=sleeps.append)

    limiter.wait()

    assert sleeps == []


def test_rate_limiter_waits_the_remaining_time_for_a_call_within_the_window():
    clock = FakeClock(start=1000.0)
    sleeps: list[float] = []
    limiter = RateLimiter(10, clock=clock, sleep=sleeps.append)

    limiter.wait()
    clock.advance(3)
    limiter.wait()

    assert sleeps == [7]


def test_rate_limiter_does_not_wait_when_enough_time_has_already_passed():
    clock = FakeClock(start=1000.0)
    sleeps: list[float] = []
    limiter = RateLimiter(10, clock=clock, sleep=sleeps.append)

    limiter.wait()
    clock.advance(15)
    limiter.wait()

    assert sleeps == []


def test_rate_limiter_waits_again_after_a_third_call_too_soon():
    clock = FakeClock(start=1000.0)
    sleeps: list[float] = []
    limiter = RateLimiter(10, clock=clock, sleep=sleeps.append)

    limiter.wait()
    clock.advance(10)
    limiter.wait()
    clock.advance(2)
    limiter.wait()

    assert sleeps == [8]


def test_download_category_walks_pages_until_has_next_page_is_false():
    page0_url = CATEGORY_URL_TEMPLATE.format(category_id="110")
    page1_url = f"{page0_url}?page=1"
    doc_a = _doc("https://www.fia.com/a.pdf")
    doc_b = _doc("https://www.fia.com/b.pdf")

    html_by_url = {page0_url: "<html0>", page1_url: "<html1>"}
    fetch_page = MagicMock(side_effect=lambda url: html_by_url[url])
    fetch_pdf = MagicMock(return_value=b"pdf-bytes")

    listing = MagicMock(spec=real_listing)
    listing.parse_listing_page.side_effect = lambda html, base_url: {
        "<html0>": [doc_a], "<html1>": [doc_b]
    }[html]
    listing.has_next_page.side_effect = lambda html: {"<html0>": True, "<html1>": False}[html]

    repository = MagicMock(spec=real_repository)
    repository.load_manifest.return_value = {}
    repository.is_downloaded.return_value = False
    repository.save_pdf.side_effect = lambda output_dir, url, content: url.rsplit("/", 1)[-1]

    result = download_category(
        "110",
        "/tmp/out",
        fetch_page=fetch_page,
        fetch_pdf=fetch_pdf,
        listing=listing,
        repository=repository,
        rate_limiter=MagicMock(),
    )

    assert fetch_page.call_args_list == [call(page0_url), call(page1_url)]
    assert {entry.source_url for entry in result.downloaded} == {doc_a.source_url, doc_b.source_url}


def test_download_category_records_full_metadata_for_a_downloaded_document():
    page0_url = CATEGORY_URL_TEMPLATE.format(category_id="110")
    doc = ListedDocument(
        title="FIA 2026 F1 Regulations - Section B [Sporting] - Iss 08 - 2026-08-05",
        source_url="https://www.fia.com/system/files/documents/foo.pdf",
        section="Section B [Sporting]",
        issue="08",
        published_date=datetime.date(2026, 8, 5),
    )

    fetch_page = MagicMock(return_value="<html0>")
    fetch_pdf = MagicMock(return_value=b"pdf-bytes")

    listing = MagicMock(spec=real_listing)
    listing.parse_listing_page.return_value = [doc]
    listing.has_next_page.return_value = False

    repository = MagicMock(spec=real_repository)
    repository.load_manifest.return_value = {}
    repository.is_downloaded.return_value = False
    repository.save_pdf.return_value = "foo.pdf"

    fixed_now = lambda: datetime.datetime(2026, 8, 8, 14, 32, 1, tzinfo=datetime.timezone.utc)  # noqa: E731

    result = download_category(
        "110",
        "/tmp/out",
        fetch_page=fetch_page,
        fetch_pdf=fetch_pdf,
        listing=listing,
        repository=repository,
        rate_limiter=MagicMock(),
        now=fixed_now,
    )

    [entry] = result.downloaded
    assert entry.title == doc.title
    assert entry.source_url == doc.source_url
    assert entry.section == "Section B [Sporting]"
    assert entry.issue == "08"
    assert entry.published_date == "2026-08-05"
    assert entry.local_filename == "foo.pdf"
    assert entry.downloaded_at == "2026-08-08T14:32:01+00:00"
    repository.record_entry.assert_called_once_with("/tmp/out", entry)


def test_download_category_continues_past_a_failed_document_and_records_it():
    doc_a = _doc("https://www.fia.com/a.pdf", title="A")
    doc_b = _doc("https://www.fia.com/b.pdf", title="B")

    fetch_page = MagicMock(return_value="<html0>")

    def fetch_pdf(url):
        if url == doc_a.source_url:
            raise RuntimeError("connection reset")
        return b"pdf-bytes"

    listing = MagicMock(spec=real_listing)
    listing.parse_listing_page.return_value = [doc_a, doc_b]
    listing.has_next_page.return_value = False

    repository = MagicMock(spec=real_repository)
    repository.load_manifest.return_value = {}
    repository.is_downloaded.return_value = False
    repository.save_pdf.return_value = "b.pdf"

    result = download_category(
        "110",
        "/tmp/out",
        fetch_page=fetch_page,
        fetch_pdf=fetch_pdf,
        listing=listing,
        repository=repository,
        rate_limiter=MagicMock(),
    )

    assert len(result.failed) == 1
    assert result.failed[0].source_url == doc_a.source_url
    assert result.failed[0].title == "A"
    assert "connection reset" in result.failed[0].reason
    assert len(result.downloaded) == 1
    assert result.downloaded[0].source_url == doc_b.source_url
    repository.record_entry.assert_called_once()


def test_download_category_rate_limits_every_request_listing_pages_and_pdfs_alike():
    doc_a = _doc("https://www.fia.com/a.pdf")

    fetch_page = MagicMock(return_value="<html0>")
    fetch_pdf = MagicMock(return_value=b"pdf-bytes")

    listing = MagicMock(spec=real_listing)
    listing.parse_listing_page.return_value = [doc_a]
    listing.has_next_page.return_value = False

    repository = MagicMock(spec=real_repository)
    repository.load_manifest.return_value = {}
    repository.is_downloaded.return_value = False
    repository.save_pdf.return_value = "a.pdf"

    rate_limiter = MagicMock()

    download_category(
        "110",
        "/tmp/out",
        fetch_page=fetch_page,
        fetch_pdf=fetch_pdf,
        listing=listing,
        repository=repository,
        rate_limiter=rate_limiter,
    )

    assert rate_limiter.wait.call_count == 2


def test_download_category_skips_a_document_already_present_in_the_manifest():
    doc_already_downloaded = _doc("https://www.fia.com/already.pdf")
    doc_new = _doc("https://www.fia.com/new.pdf")

    fetch_page = MagicMock(return_value="<html0>")
    fetch_pdf = MagicMock(return_value=b"pdf-bytes")

    listing = MagicMock(spec=real_listing)
    listing.parse_listing_page.return_value = [doc_already_downloaded, doc_new]
    listing.has_next_page.return_value = False

    repository = MagicMock(spec=real_repository)
    repository.load_manifest.return_value = {doc_already_downloaded.source_url: {}}
    repository.is_downloaded.side_effect = lambda manifest, url: url in manifest
    repository.save_pdf.return_value = "new.pdf"

    result = download_category(
        "110",
        "/tmp/out",
        fetch_page=fetch_page,
        fetch_pdf=fetch_pdf,
        listing=listing,
        repository=repository,
        rate_limiter=MagicMock(),
    )

    assert result.skipped == [doc_already_downloaded.source_url]
    assert [entry.source_url for entry in result.downloaded] == [doc_new.source_url]
    fetch_pdf.assert_called_once_with(doc_new.source_url)
    repository.save_pdf.assert_called_once()


def test_download_category_does_not_rate_limit_or_fetch_for_skipped_documents():
    doc_already_downloaded = _doc("https://www.fia.com/already.pdf")

    fetch_page = MagicMock(return_value="<html0>")
    fetch_pdf = MagicMock(return_value=b"pdf-bytes")

    listing = MagicMock(spec=real_listing)
    listing.parse_listing_page.return_value = [doc_already_downloaded]
    listing.has_next_page.return_value = False

    repository = MagicMock(spec=real_repository)
    repository.load_manifest.return_value = {doc_already_downloaded.source_url: {}}
    repository.is_downloaded.side_effect = lambda manifest, url: url in manifest

    rate_limiter = MagicMock()

    result = download_category(
        "110",
        "/tmp/out",
        fetch_page=fetch_page,
        fetch_pdf=fetch_pdf,
        listing=listing,
        repository=repository,
        rate_limiter=rate_limiter,
    )

    assert result.skipped == [doc_already_downloaded.source_url]
    fetch_pdf.assert_not_called()
    repository.save_pdf.assert_not_called()
    repository.record_entry.assert_not_called()
    # Only the listing-page fetch is rate-limited; the skipped document incurs no wait.
    assert rate_limiter.wait.call_count == 1
