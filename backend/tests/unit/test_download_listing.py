import datetime

from src.modules.download.listing import ListedDocument, has_next_page, parse_listing_page

BASE_URL = "https://www.fia.com"

_ONE_ENTRY_PAGE = """
<html><body>
<div class="list-item">
  <div class="content">
    <a href="/system/files/documents/fia_2026_f1_regulations_-_section_b_sporting_-_iss_08_-_2026-08-05_7.pdf" download target="_blank">
      <div class="tag"> 2026 Regulations </div>
      <div class="file-type"> <div class="pdf"></div> </div>
      <div class="title"> FIA 2026 F1 Regulations - Section B [Sporting] - Iss 08 - 2026-08-05 </div>
      <div class="published"> Published on <span class="date-display-single">05.08.26</span> </div>
    </a>
  </div>
</div>
</body></html>
"""

_MISSING_FIELDS_PAGE = """
<html><body>
<div class="list-item">
  <div class="content">
    <a href="/system/files/documents/some_untitled_document.pdf" download target="_blank">
      <div class="tag"> Older Regulations </div>
      <div class="file-type"> <div class="pdf"></div> </div>
      <div class="title"> FIA Historic Regulations Bundle </div>
    </a>
  </div>
</div>
</body></html>
"""

_NO_TITLE_PAGE = """
<html><body>
<div class="list-item">
  <div class="content">
    <a href="/system/files/documents/no_title_document.pdf" download target="_blank">
      <div class="tag"> Older Regulations </div>
      <div class="file-type"> <div class="pdf"></div> </div>
    </a>
  </div>
</div>
<div class="list-item">
  <div class="content">
    <a href="/system/files/documents/has_a_title.pdf" download target="_blank">
      <div class="title"> A Real Document </div>
    </a>
  </div>
</div>
</body></html>
"""

_PAGE_WITH_NEXT_LINK = """
<ul class="pager"><li class="pager-current first">1</li>
<li class="pager-item"><a title="Go to page 2" href="/regulation/category/110?page=1">2</a></li>
<li class="pager-next"><a title="Go to next page" href="/regulation/category/110?page=1">next &#8250;</a></li>
<li class="pager-last last"><a title="Go to last page" href="/regulation/category/110?page=7">last &raquo;</a></li>
</ul>
"""

_LAST_PAGE_NO_NEXT_LINK = """
<ul class="pager"><li class="pager-item first"><a title="Go to first page" href="/regulation/category/110">1</a></li>
<li class="pager-current last">8</li>
</ul>
"""


def test_parse_listing_page_extracts_title_source_url_section_issue_and_date():
    [doc] = parse_listing_page(_ONE_ENTRY_PAGE, BASE_URL)

    assert doc.title == "FIA 2026 F1 Regulations - Section B [Sporting] - Iss 08 - 2026-08-05"
    assert doc.source_url == (
        "https://www.fia.com/system/files/documents/"
        "fia_2026_f1_regulations_-_section_b_sporting_-_iss_08_-_2026-08-05_7.pdf"
    )
    assert doc.section == "Section B [Sporting]"
    assert doc.issue == "08"
    assert doc.published_date == datetime.date(2026, 8, 5)


def test_parse_listing_page_resolves_relative_urls_against_base_url():
    [doc] = parse_listing_page(_ONE_ENTRY_PAGE, "https://www.fia.com")

    assert doc.source_url.startswith("https://www.fia.com/")


def test_parse_listing_page_handles_a_title_that_does_not_match_the_section_or_issue_pattern():
    [doc] = parse_listing_page(_MISSING_FIELDS_PAGE, BASE_URL)

    assert doc.title == "FIA Historic Regulations Bundle"
    assert doc.section is None
    assert doc.issue is None


def test_parse_listing_page_handles_a_missing_published_date():
    [doc] = parse_listing_page(_MISSING_FIELDS_PAGE, BASE_URL)

    assert doc.published_date is None


def test_parse_listing_page_skips_an_entry_with_no_title_but_keeps_the_rest():
    docs = parse_listing_page(_NO_TITLE_PAGE, BASE_URL)

    assert len(docs) == 1
    assert docs[0].title == "A Real Document"


def test_parse_listing_page_returns_empty_list_for_a_page_with_no_entries():
    assert parse_listing_page("<html><body></body></html>", BASE_URL) == []


def test_has_next_page_is_true_when_a_pager_next_link_is_present():
    assert has_next_page(_PAGE_WITH_NEXT_LINK) is True


def test_has_next_page_is_false_when_no_pager_next_link_is_present():
    assert has_next_page(_LAST_PAGE_NO_NEXT_LINK) is False


def test_has_next_page_is_false_when_there_is_no_pager_at_all():
    assert has_next_page("<html><body>No results.</body></html>") is False


def test_listed_document_is_a_plain_dataclass_with_the_expected_fields():
    doc = ListedDocument(
        title="t", source_url="u", section="s", issue="i", published_date=datetime.date(2026, 1, 1)
    )

    assert doc.title == "t"
    assert doc.source_url == "u"
    assert doc.section == "s"
    assert doc.issue == "i"
    assert doc.published_date == datetime.date(2026, 1, 1)
