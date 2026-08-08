# Implementation Plan: FIA Regulation PDF Downloader

**Branch**: `009-fia-pdf-download` | **Date**: 2026-08-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-fia-pdf-download/spec.md`

## Summary

A standalone CLI tool that walks the FIA's public regulation listing pages for
a category, downloads every regulation PDF it finds (including superseded
issues, not just the latest), and writes each document's metadata (title,
source URL, section, issue/revision, publish date, download timestamp) to a
manifest file alongside the archive. Re-running the tool skips any document
whose source URL is already present in the manifest, and every request to the
source site is throttled to the site's published 10-second crawl-delay. This
tool's output (the local PDF archive) is a manual input to the existing,
separate ingestion CLI — it does not call ingestion itself.

## Technical Context

**Language/Version**: Python 3.12 (matches the rest of `backend/`)

**Primary Dependencies**: `httpx` (already a dependency, used here for both
listing-page and PDF requests instead of adding `requests`), `beautifulsoup4`
(new — HTML parsing of the listing pages; the alternative, hand-rolled regex
parsing of Drupal-generated HTML, was rejected as too fragile against markup
changes)

**Storage**: Local filesystem — downloaded PDFs plus a single JSON manifest
file per output directory (see `data-model.md`); no database involved

**Testing**: pytest, following the existing `modules/ingestion/` pattern —
unit tests with the HTTP client and filesystem mocked/injected, no test in
the automated suite makes a real network call to the FIA site (Constitution
Principle II: tests depending on live external services must be isolated
and labeled — this feature avoids the question entirely by not committing
any live-network test; live behavior is validated manually per
`quickstart.md`)

**Target Platform**: Same environment as the existing backend — run manually
from a developer/operator's machine or CI-adjacent shell, exactly like
`modules/ingestion/cli.py` already is

**Project Type**: Backend-only CLI addition to the existing `backend/`
codebase (no frontend, no new HTTP endpoint) — mirrors `modules/ingestion/`'s
shape (`service.py` + `repository.py`-style persistence + `cli.py`, no
`router.py`/`schemas.py` since nothing is exposed over HTTP)

**Performance Goals**: None beyond correctness — total run time is dominated
by the mandatory 10-second crawl-delay between requests (FR-005), not by
anything this tool controls

**Constraints**: MUST wait ≥10s between every request to the source site
(listing pages and PDF downloads alike); MUST NOT re-download a document
already recorded in the manifest; MUST continue past an individual document
failure rather than aborting the run

**Scale/Scope**: Observed today: ~240 documents across 8 listing pages for
category 110; the page count is not fixed and MUST be discovered at runtime
by following pagination rather than assumed

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Test-First Development**: Applies as normal — tests for listing
  parsing, manifest/repository behavior, and run orchestration are written
  before their implementation in `tasks.md`. PASS.
- **II. Comprehensive Unit Testing**: All business logic (listing-page
  parsing, dedup-by-manifest logic, pagination walking, failure handling) is
  unit-testable with the HTTP client injected/mocked, per the existing
  `modules/ingestion/` DI pattern (`service.py` accepting collaborators as
  keyword defaults). No automated test depends on live network access. PASS.
- **III. API Contract Consistency**: Not applicable in the OpenAPI sense —
  this feature adds no FastAPI endpoint and touches no request/response
  contract. The CLI's own interface (arguments, exit behavior) and the
  manifest file's shape are documented in `contracts/` instead, consistent
  with this principle's intent of no undocumented contract drift. PASS.
- **IV. Clean Code & Readability**: Applies as normal. PASS.
- **V. Separation of Concerns**: This feature is a new, self-contained
  `modules/download/` bounded domain (service + repository-style persistence
  + CLI), matching the required module shape. It does not touch retrieval,
  presentation, or the existing `modules/ingestion/` or `modules/auth/`
  code. Note: Principle V's department-aware authorization requirement
  governs *serving* regulation content to app users (chat/retrieval) — this
  tool only *acquires* source PDFs from the FIA's own public site for an
  operator to later ingest manually; it never serves content to an
  authenticated end user, so that requirement doesn't apply here. PASS.

No violations — Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/009-fia-pdf-download/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   └── modules/
│       └── download/
│           ├── __init__.py
│           ├── listing.py       # Parses a listing page's HTML into document records; detects next page
│           ├── repository.py    # Manifest read/write, dedup lookup, PDF file writes to disk
│           ├── service.py       # Orchestrates: walk pages, rate-limit, download, skip already-known, collect run summary
│           └── cli.py           # Entry point: python -m src.modules.download.cli --category <id> [--output-dir <path>]
└── tests/
    └── unit/
        ├── test_download_listing.py
        ├── test_download_repository.py
        └── test_download_service.py

data/                             # NEW top-level dir, gitignored — downloaded
└── regulations/                  # PDFs + manifest.json live here, never committed
    └── <category-id>/
        ├── manifest.json
        └── *.pdf
```

**Structure Decision**: Backend-only addition following the existing
`modules/ingestion/` shape exactly (service + repository + cli, no router).
Downloaded artifacts live in a new top-level `data/` directory (sibling to
`backend/`, `frontend/`, `db/`) rather than inside `backend/src/`, since it's
runtime output, not source — and it's added to `.gitignore` during
implementation so PDFs are never committed.

## Complexity Tracking

*No violations — table intentionally omitted.*
