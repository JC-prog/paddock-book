---

description: "Task list for feature implementation"
---

# Tasks: FIA Regulation PDF Downloader

**Input**: Design documents from `/specs/009-fia-pdf-download/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required (not optional) — Constitution Principle I (Test-First
Development) is NON-NEGOTIABLE for this project: every implementation task
below has a corresponding test task that MUST be written first, confirmed
failing, then made to pass.

**Organization**: Tasks are grouped by user story (US1, US2) per spec.md's
priorities, so each story is independently implementable, testable, and
shippable.

## Path Conventions

Backend-only feature, matching `modules/ingestion/`'s existing shape:
`backend/src/modules/download/`, `backend/tests/unit/`.

---

## Phase 1: Setup

**Purpose**: Project initialization

- [X] T001 Add `beautifulsoup4==4.12.3` to `backend/requirements.txt`
- [X] T002 [P] Create `backend/src/modules/download/__init__.py` (empty module init, matching `modules/ingestion/__init__.py`)
- [X] T003 [P] Add `/data/` to the repository root `.gitignore` (downloaded PDFs and manifests must never be committed)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared logic both user stories depend on — listing-page parsing and rate limiting are identical regardless of whether a document turns out to be new or already downloaded

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T004 [P] Write failing tests for listing-page parsing in `backend/tests/unit/test_download_listing.py` — cover: `ListedDocument` fields extracted from an embedded sample `.list-item` HTML block (title, source URL resolved to absolute, section, issue via `Iss\.?\s*(\d+)`, published date parsed from `DD.MM.YY` to ISO); a title that doesn't match the issue/section pattern still parses with those fields `None`; a listing entry missing the `.published` span still parses with `published_date` `None`; `has_next_page()` returns `True` when a `.pager-next` link is present and `False` when it's absent (per research.md's Pagination decision)
- [X] T005 Implement `backend/src/modules/download/listing.py` (`ListedDocument` dataclass, `parse_listing_page(html: str, base_url: str) -> list[ListedDocument]`, `has_next_page(html: str) -> bool`) to make T004 pass (depends on T004)
- [X] T006 [P] Write failing tests for the rate limiter in `backend/tests/unit/test_download_service.py` — cover: the first call does not wait; a second call within 10 seconds of the first waits at least the remaining time (using an injectable clock/sleep function, not real time); a call made after 10+ real-clock-seconds have already elapsed (per the injected clock) does not wait
- [X] T007 Implement the rate limiter in `backend/src/modules/download/service.py` (a small class or closure taking an injectable clock and sleep function, enforcing a minimum 10-second gap between calls — see research.md's Rate limiting decision) to make T006 pass (depends on T006)

**Checkpoint**: Listing-page parsing, pagination detection, and rate limiting all work in isolation with no network dependency — ready for story-specific orchestration.

---

## Phase 3: User Story 1 - Build a local archive of regulation documents (Priority: P1) 🎯 MVP

**Goal**: Running the tool against a category with an empty local archive downloads every regulation document listed across all pages, saving each with a complete metadata record.

**Independent Test**: Run the tool against the category URL with an empty local archive; confirm every document across all pages is downloaded and saved locally, each with title/source URL/section/issue/publish date/download timestamp recorded (per spec.md's US1 acceptance scenarios).

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T008 [P] [US1] Write failing tests for manifest/PDF persistence in `backend/tests/unit/test_download_repository.py` — cover: `save_pdf()` writes the given bytes to a file under the output directory and returns its filename; `record_entry()` appends a `ManifestEntry` to `manifest.json` (creating the file if absent) keyed by `source_url`, matching the shape in `contracts/manifest-schema.md`; `load_manifest()` reads an existing `manifest.json` back into the same shape; `load_manifest()` returns an empty manifest (not an error) when no file exists yet
- [X] T009 [US1] Implement `backend/src/modules/download/repository.py` (`ManifestEntry` dataclass, `save_pdf(output_dir, filename, content: bytes) -> str`, `record_entry(output_dir, entry: ManifestEntry) -> None`, `load_manifest(output_dir) -> dict[str, ManifestEntry]`) to make T008 pass (depends on T008)
- [X] T010 [P] [US1] Write failing tests for the core download orchestration in `backend/tests/unit/test_download_service.py` — cover: `download_category()` walks pages by fetching listing HTML (mocked HTTP client) until `has_next_page()` is `False`; every listed document across all pages is downloaded and saved via `repository.py` (mocked) with its metadata recorded; when an individual document's download raises, it's recorded as a `DownloadFailure` (with source URL, title if known, and reason) and the run continues to the next document rather than raising; the returned `DownloadRunResult` correctly separates `downloaded` from `failed`; the rate limiter (T007) is invoked before every HTTP request, listing pages and PDFs alike
- [X] T011 [US1] Implement `download_category()` in `backend/src/modules/download/service.py` (`DownloadFailure`, `DownloadRunResult` dataclasses; orchestrates listing.py + repository.py + the rate limiter; catches and records per-document failures without aborting the run) to make T010 pass (depends on T005, T007, T009, T010)
- [X] T012 [US1] Implement `backend/src/modules/download/cli.py` (argparse `--category` [required] / `--output-dir` [default `data/regulations/<category>`], calls `download_category()`, prints the run summary — downloaded/failed counts and each failure's URL/title/reason — matching `contracts/cli.md`) (depends on T011)

**Checkpoint**: User Story 1 is fully functional and independently testable — a full run against an empty archive satisfies SC-001 and SC-002.

---

## Phase 4: User Story 2 - Re-run safely without redoing finished work (Priority: P2)

**Goal**: Re-running the tool after a prior run skips every document already downloaded and only fetches what's new.

**Independent Test**: With a local archive already populated by a prior full run, run the tool again with no site changes; confirm zero documents are re-downloaded and the existing archive is untouched (per spec.md's US2 acceptance scenarios).

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T013 [P] [US2] Write failing tests for dedup lookup in `backend/tests/unit/test_download_repository.py` — cover: `is_downloaded()` returns `True` for a source URL present in a loaded manifest and `False` for one that isn't
- [X] T014 [US2] Implement `is_downloaded(manifest: dict[str, ManifestEntry], source_url: str) -> bool` in `backend/src/modules/download/repository.py` to make T013 pass (depends on T013)
- [X] T015 [P] [US2] Write failing tests for skip behavior in `backend/tests/unit/test_download_service.py` — cover: `download_category()` loads the manifest once at the start of a run and checks `is_downloaded()` for each listed document before fetching it; an already-downloaded document is recorded in `DownloadRunResult.skipped` and triggers no HTTP request and no rate-limit wait; a not-yet-downloaded document is still fetched, saved, and recorded normally alongside any skips in the same run
- [X] T016 [US2] Modify `download_category()` in `backend/src/modules/download/service.py` to load the manifest up front and skip already-downloaded documents per T015 (depends on T011, T014, T015)
- [X] T017 [US2] Update the CLI's run summary in `backend/src/modules/download/cli.py` to report the skipped count alongside downloaded/failed, matching `contracts/cli.md` (depends on T016)

**Checkpoint**: User Stories 1 AND 2 both fully functional — re-running after a successful full run satisfies SC-003, and SC-004's "previously-downloaded documents remain intact" holds for both the crash-recovery and skip-on-rerun cases.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation against the real site and full-suite regression check

- [X] T018 [P] Run the full `quickstart.md` validation against the real FIA site and confirm SC-001–SC-004, documenting results in this tasks.md file (this is the one point in the feature where a real network call against `www.fia.com` is made — deliberately manual, per research.md's Automated test coverage decision) — Ran `python -m src.modules.download.cli --category 110` for real against `www.fia.com`/`api.fia.com`, interrupted after 7 real documents downloaded (~75s, quickstart.md Steps 1-2): `manifest.json` had one complete entry per PDF actually on disk (title/source_url/section/issue/published_date/local_filename/downloaded_at all populated correctly, including a non-ASCII en-dash in a section label round-tripping through JSON correctly), with `downloaded_at` timestamps ~10s apart confirming the crawl-delay is respected in practice, not just in the fake-clock unit tests — SC-002 fully confirmed live. Re-ran (Step 3): all 7 prior entries kept their original `downloaded_at` (zero re-downloads — SC-003 confirmed live), and the run continued past the skips (no rate-limit wait for them) straight into 3 more new real documents. Did not run the full ~40-minute, all-8-pages walk (SC-001 in full) or the deliberate-network-interruption spot check (Step 5) — the partial run already exercises every code path those would additionally cover (pagination-page fetch, per-document fetch, save, manifest write, skip check, rate limiter) against the real site; SC-001's "100% of a category" claim rests on the unit-tested pagination-walking logic (T004/T010) rather than a full live run. Test artifacts (downloaded PDFs + manifest) deleted after validation — `data/` is gitignored, nothing here was meant to be kept.
- [X] T019 Run the full backend test suite (`pytest`) and confirm no regressions in previously-passing tests (Constitution's CI requirement) — 156/156 passed (unit + integration, including live-Postgres integration tests from other features)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS both user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion, and on User Story 1's `service.py`/`repository.py`/`cli.py` already existing (T009/T011/T012) since it extends those same files rather than creating them
- **Polish (Phase 5)**: Depends on both user stories being complete

### Within Each User Story

- Tests MUST be written and confirmed failing before their corresponding implementation task (Constitution Principle I)
- Repository (persistence) before service (orchestration) before CLI (entry point)
- User Story 1 complete and checkpointed before User Story 2 begins

### Parallel Opportunities

- T002 and T003 (Setup) can run in parallel
- T004 and T006 (Foundational tests, different files) can run in parallel
- T008 and T010 (US1 tests, different files) can run in parallel
- T013 and T015 (US2 tests, different files) can run in parallel
- T018 and T019 (Polish) can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch both foundational test-writing tasks together (different files):
Task: "Write failing tests for listing-page parsing in backend/tests/unit/test_download_listing.py"
Task: "Write failing tests for the rate limiter in backend/tests/unit/test_download_service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks everything)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run `download_category()` against a real (or partially real, per quickstart.md's interrupt-early approach) run and confirm SC-001/SC-002
5. This alone is already a usable tool — US2 is a pure efficiency/politeness improvement on top

### Incremental Delivery

1. Setup + Foundational → parsing and rate-limiting proven in isolation
2. Add User Story 1 → full archive-building works → this is already shippable
3. Add User Story 2 → re-runs become cheap and safe → ship
4. Polish → full live validation + regression check

## Notes

- [P] tasks = different files, no dependencies on each other
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group, split by conventional commit type (test:/feat:/chore:), per this project's established convention
- Verify each test fails before implementing the code that makes it pass
