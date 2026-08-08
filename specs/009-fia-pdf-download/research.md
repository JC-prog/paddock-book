# Research: FIA Regulation PDF Downloader

All findings below were confirmed against the live site
(`https://api.fia.com/regulation/category/110`, which resolves to the same
Drupal-rendered HTML as `https://www.fia.com/regulation/category/110`) and
its `robots.txt` before this spec/plan was written — nothing here is
guessed.

## Source site structure

**Decision**: Treat the category URL as an HTML page to parse (via
BeautifulSoup), not a JSON API — despite the `api.` subdomain, the response
is the same server-rendered Drupal HTML as the `www.` site.

**Rationale**: `curl`-ing the URL directly returns
`<!DOCTYPE html ... Drupal 7 ...>`, with `<link rel="canonical" href="https://www.fia.com/regulation/category/110" />`. There is no JSON content
negotiation available (an `Accept: application/json` header made no
difference).

**Alternatives considered**: Looking for an undocumented JSON endpoint —
rejected; none was found, and reverse-engineering a private API is more
fragile than parsing the public HTML the site itself renders for browsers.

## Pagination

**Decision**: Walk pages via `?page=N` (0-indexed — the first page is
implicit/no query param, page 2 of the UI is `?page=1`, etc.), stopping when
a page's listing contains a `.pager-next` link is absent (i.e., stop
after the page that has no "next ›" link).

**Rationale**: Confirmed via the live page's pager markup:
`<li class="pager-next"><a ... href="/regulation/category/110?page=1">next ›</a></li>` and `<li class="pager-last last"><a ... href="/regulation/category/110?page=7">last »</a></li>`. Category 110 currently spans pages 0–7 (8 pages, ~240
documents, 30 per page). This count is not fixed and must not be hardcoded.

**Alternatives considered**: Reading the "last »" link's page number up
front and looping to it directly — rejected in favor of the more robust
"stop when there's no next link" approach, which keeps working even if a
future page's layout omits the "last" shortcut or the count changes between
the first request and the last.

## Per-document metadata extraction

**Decision**: Parse metadata from each listing entry's own structured HTML,
not from the PDF filename. Each entry has the shape:

```html
<div class="list-item"><div class="content">
  <a href="/system/files/documents/....pdf" download target="_blank">
    <div class="tag">2026 Regulations</div>
    <div class="title">FIA 2026 F1 Regulations - Section B [Sporting] - Iss 08 - 2026-08-05</div>
    <div class="published">Published on <span class="date-display-single">05.08.26</span></div>
  </a>
</div></div>
```

- `title` → the `.title` div's text, verbatim (already self-describes
  section and issue, e.g. "Section B [Sporting]", "Iss 08")
- `source_url` → the anchor's `href`, resolved against `https://www.fia.com`
  (hrefs on the page are root-relative, e.g. `/system/files/documents/...`)
- `section` → extracted from the title text between the "Section X" marker
  and the following bracketed label (e.g. `Section B [Sporting]` →
  `Section B [Sporting]`, stored as-is; no further normalization, since
  FR-007 explicitly keeps department/category assignment out of scope)
- `issue` → extracted from the title via a case-insensitive `Iss\.?\s*(\d+)`
  pattern; stored as `None` if the title doesn't match (some early documents
  use different title conventions)
- `published_date` → the `.published .date-display-single` span's text
  (format `DD.MM.YY`, e.g. `05.08.26`), parsed into an ISO `YYYY-MM-DD`
  date; stored as `None` if the span is missing (per spec Edge Cases: an
  incomplete record must not fail the whole download)

**Rationale**: The `.title` and `.published` fields are dedicated,
structured elements the site itself renders — far more reliable than
regexing the PDF filename (which has inconsistent conventions across older
documents, e.g. some omit the `iss_NN` segment or use different separators).

**Alternatives considered**: Filename-based parsing — rejected as the
primary source for exactly that inconsistency; still implicitly available
as a fallback if a future document's title text doesn't parse, but not
built out now (YAGNI — no observed case currently requires it).

## HTML parsing library

**Decision**: `beautifulsoup4` (new dependency), with Python's built-in
`html.parser` backend (no `lxml` dependency needed).

**Rationale**: The project has no existing HTML-parsing dependency.
BeautifulSoup is the standard, well-maintained choice for this and handles
Drupal's imperfect HTML robustly. `html.parser` avoids adding `lxml` (a
compiled dependency) for a page structure that doesn't need XPath or
malformed-XML tolerance beyond what `html.parser` already provides.

**Alternatives considered**: Regex-only parsing — rejected as too fragile
against markup changes and whitespace variation (seen firsthand: the
`.title`/`.published` div contents have inconsistent leading/trailing
whitespace and blank lines in the raw HTML).

## HTTP client

**Decision**: `httpx` (already a dependency via FastAPI's test client) for
both listing-page GETs and PDF binary downloads.

**Rationale**: Avoids adding a redundant HTTP client (`requests`) when one
is already present and fully capable for simple synchronous GETs.

**Alternatives considered**: `requests` — rejected purely to avoid a
duplicate dependency; no functional difference for this use case.

## Rate limiting / crawl-delay

**Decision**: A single rate limiter applied before every HTTP request this
tool makes to the source site (listing pages and PDF downloads alike),
enforcing a minimum 10-second gap since the previous request.

**Rationale**: `https://www.fia.com/robots.txt` specifies `Crawl-delay: 10`
under `User-agent: *`, with no `Disallow` rule covering `/regulation/` or
`/system/files/documents/`. Applying the delay uniformly (not just between
listing-page fetches) is the straightforward reading of "be a good citizen
of this site's stated crawl policy" and keeps the rate-limiting logic in
one place rather than duplicated at each call site.

**Alternatives considered**: Only rate-limiting listing-page requests (since
those are the ones repeatedly hitting the same Drupal view) — rejected
since PDF downloads are still requests to the same site and the policy
doesn't distinguish by content type.

## Manifest storage format

**Decision**: A single `manifest.json` file per output directory, mapping
each document's `source_url` to its metadata record (including the local
filename it was saved as and the download timestamp). Written after each
successful document download, not batched at the end of the run.

**Rationale**: `source_url` is already the natural, guaranteed-unique dedup
key (FR-004), so a URL-keyed manifest answers "is this already downloaded?"
in a single lookup without scanning the output directory. Writing after
each success (not batching) means a run interrupted partway through (Edge
Case: source site becomes unreachable mid-run) still leaves an accurate,
usable manifest for the documents that did complete — satisfying SC-004's
"previously-downloaded documents remain intact" requirement without extra
recovery logic.

**Alternatives considered**:
- One JSON sidecar file per PDF (e.g. `foo.pdf` + `foo.json`) — rejected as
  the primary mechanism because it requires scanning every sidecar file on
  each run just to answer "what's already downloaded," which gets slower as
  the archive grows; a single manifest is a straightforward
  read-parse-lookup instead.
- A SQLite or Postgres-backed record — rejected as unnecessary weight for a
  single-operator local archive with no concurrent access and no query
  needs beyond "does this URL exist" and "list everything downloaded,"
  both trivially served by a JSON file at this scale (hundreds, not
  millions, of records).

## Automated test coverage vs. live network access

**Decision**: No automated test makes a real request to the FIA site. All
`listing.py`/`service.py` unit tests use embedded sample HTML strings
(mirroring the existing `modules/ingestion/parser.py` tests, which embed a
hand-built minimal PDF rather than reading a fixture file) and an
injected/mocked HTTP client, following the same DI pattern already used
throughout `modules/ingestion/` and `modules/chat/` (`service.py` accepting
collaborators as keyword-default parameters).

**Rationale**: Constitution Principle II requires tests depending on live
external services to be isolated and labeled as integration tests, not
counted as unit coverage — and this project has no existing pattern for an
"internet-dependent" integration test (the existing `tests/integration/`
suite means "real local Postgres," which CI already provisions; it does not
mean "real internet access," which CI does not reliably have and which
would also violate the 10-second crawl-delay if run on every CI push).
Real end-to-end behavior against the live site is validated manually per
`quickstart.md`, the same way this project has always handled
Bedrock-dependent live paths (features 006 and 008) that CI can't exercise.

**Alternatives considered**: A `pytest.mark.live` / opt-in test hitting the
real site — rejected for now as more infrastructure than this feature
needs; nothing currently blocks adding one later if repeated manual
`quickstart.md` runs become tedious.
