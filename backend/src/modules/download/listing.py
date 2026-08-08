import datetime
import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

_SECTION_PATTERN = re.compile(r"Section\s+\w+\s*\[[^\]]+\]")
_ISSUE_PATTERN = re.compile(r"Iss\.?\s*(\d+)", re.IGNORECASE)


@dataclass
class ListedDocument:
    title: str
    source_url: str
    section: str | None
    issue: str | None
    published_date: datetime.date | None


def parse_listing_page(html: str, base_url: str) -> list[ListedDocument]:
    soup = BeautifulSoup(html, "html.parser")
    documents = []

    for anchor in soup.select(".list-item .content a"):
        title_element = anchor.select_one(".title")
        if title_element is None:
            continue
        title = title_element.get_text(strip=True)
        if not title:
            continue

        href = anchor.get("href")
        source_url = urljoin(base_url, href) if href else ""

        documents.append(
            ListedDocument(
                title=title,
                source_url=source_url,
                section=_extract_section(title),
                issue=_extract_issue(title),
                published_date=_extract_published_date(anchor),
            )
        )

    return documents


def has_next_page(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    return soup.select_one("li.pager-next") is not None


def _extract_section(title: str) -> str | None:
    match = _SECTION_PATTERN.search(title)
    return match.group(0) if match else None


def _extract_issue(title: str) -> str | None:
    match = _ISSUE_PATTERN.search(title)
    return match.group(1) if match else None


def _extract_published_date(anchor) -> datetime.date | None:
    date_element = anchor.select_one(".published .date-display-single")
    if date_element is None:
        return None
    text = date_element.get_text(strip=True)
    try:
        return datetime.datetime.strptime(text, "%d.%m.%y").date()
    except ValueError:
        return None
