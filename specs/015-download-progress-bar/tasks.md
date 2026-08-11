---

description: "Task list for feature implementation"
---

# Tasks: Download CLI Progress Bar

**Input**: Design documents from `/specs/015-download-progress-bar/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required (not optional) — Constitution Principle I (Test-First
Development) is NON-NEGOTIABLE for this project: every implementation task
below has a corresponding test task that MUST be written first, confirmed
failing, then made to pass.

**Organization**: Tasks are grouped by user story (US1, US2) per spec.md's
priorities.

## Path Conventions

`backend/requirements.txt`, `backend/src/modules/download/{service,cli}.py`,
`backend/tests/unit/test_download_{service,cli}.py`.

---

## Phase 1: Setup

**Purpose**: The new dependency this feature needs

- [X] T001 [P] Add `tqdm` to `backend/requirements.txt` and install it
  into the backend venv

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `download/service.py` needs a way to count the total and
report progress before either rendering mode (US1's interactive bar,
US2's plain redirected lines) has anything to wire itself to.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T002 [P] Write failing tests for `count_documents_in_category()`
  in `backend/tests/unit/test_download_service.py` (extend) — cover:
  walks every listing page via the existing `listing.parse_listing_page()`/
  `has_next_page()` calls (mocked, matching this file's existing style)
  and returns the sum of documents found across all pages; rate-limits
  each page fetch (reusing the existing `RateLimiter`/`rate_limiter`
  DI parameter, per this file's existing rate-limiting tests); calls
  `on_page_counted(page_number)` after each page is counted, if
  provided; never calls `fetch_pdf` at all (research.md — this pass
  never downloads anything)
- [X] T003 Implement `count_documents_in_category()` in
  `backend/src/modules/download/service.py` to make T002 pass (depends
  on T002)
- [X] T004 [P] Write failing tests for `download_category()`'s new
  `on_progress` parameter in `backend/tests/unit/test_download_service.py`
  (extend) — cover: called once after every document is processed —
  downloaded, skipped, and failed alike — with the correct running
  total processed so far (not the total itself); omitting `on_progress`
  entirely changes nothing about existing behavior (regression check
  against this file's pre-existing `download_category()` tests)
- [X] T005 Implement the `on_progress` parameter in `download_category()`
  to make T004 pass (depends on T004)
- [X] T006 [P] Write failing tests for `download_category()`'s new
  `on_failure` parameter in `backend/tests/unit/test_download_service.py`
  (extend) — cover: called immediately with the `DownloadFailure` when
  a document fails, before that same document's `on_progress` call
  (data-model.md); never called for a document that downloads or skips
  successfully; omitting `on_failure` entirely changes nothing
- [X] T007 Implement the `on_failure` parameter in `download_category()`
  to make T006 pass (depends on T005, T006)

**Checkpoint**: `service.py` can report a total and progress/failures
as they happen. `cli.py` doesn't render any of it yet.

---

## Phase 3: User Story 1 - Watch download progress in real time (Priority: P1)

**Goal**: An operator running the CLI in a real terminal sees live
counting feedback, then a bounded `X/Y` bar advancing as documents are
processed, with failures surfaced immediately without corrupting the
bar.

**Independent Test**: Run the CLI in an interactive terminal against a
category with documents across multiple listing pages; observe
counting feedback, then a bounded bar reporting a total before download
starts and advancing to that total as it runs.

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T008 [P] [US1] Write failing tests for interactive (TTY) progress
  rendering in `backend/tests/unit/test_download_cli.py` (NEW) — with
  `sys.stdout.isatty` mocked to return `True`, and
  `count_documents_in_category`/`download_category` mocked — cover:
  `count_documents_in_category` is called with an `on_page_counted`
  callback before `download_category` is ever called (counting happens
  first, per research.md's separate-passes decision); once counting
  returns a total, a bounded `tqdm` progress bar is created with that
  total; `download_category` is called with `on_progress` wired to
  advance that bar and `on_failure` wired to print via `tqdm.write()`
  (not a plain `print()`, which would corrupt the bar's live redraw)
- [X] T009 [US1] Implement TTY-mode rendering in
  `backend/src/modules/download/cli.py` (an `isatty()` check selecting
  this path; an indeterminate `tqdm` bar for the counting phase per
  research.md; a bounded `tqdm` bar for the download phase;
  `tqdm.write()` for immediate failure lines) to make T008 pass
  (depends on T003, T005, T007, T008)

**Checkpoint**: User Story 1 is fully functional and independently
testable in a real terminal — SC-001, SC-002, and SC-006 hold.

---

## Phase 4: User Story 2 - Redirected output stays readable (Priority: P2)

**Goal**: An operator who redirects a run's output to a file gets
readable, throttled plain-text progress lines — never raw control-code
corruption, and never total silence either.

**Independent Test**: Run the CLI with output redirected to a file;
read the file back afterward and confirm it contains readable text
reflecting progress over time, not escape-sequence noise.

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T010 [P] [US2] Write failing tests for non-TTY (redirected)
  rendering in `backend/tests/unit/test_download_cli.py` (extend) —
  with `sys.stdout.isatty` mocked to return `False` — cover: no `tqdm`
  object is ever constructed in this path (research.md — plain lines
  only); counting phase prints one plain line per page counted (e.g.
  `Counting documents... (page 4)`); once the total is known, one line
  reports it; during download, a progress line prints only when
  cumulative progress crosses each 10% boundary of the total, not on
  every single document (contracts/cli-output.md); a failure prints
  its own line immediately regardless of the 10%-boundary throttle
  (FR-002a applies identically in both rendering modes)
- [X] T011 [US2] Implement non-TTY plain-line rendering in
  `backend/src/modules/download/cli.py` (extend) to make T010 pass
  (depends on T009, T010)

**Checkpoint**: Both user stories are fully functional — SC-003 holds
(redirected output stays readable and informative), and the feature is
complete end-to-end.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation against the real FIA site, plus
full-suite regression check

- [X] T012 [P] Run the full `quickstart.md` validation against the
  real site, confirming FR-001–FR-008 / SC-001–SC-006, documenting
  results in this tasks.md file

  **Results (live-validated against the real FIA site, category 110,
  non-interactive/redirected mode — the harder of the two rendering
  paths to get right per research.md — across two full CLI invocations
  against the same `--output-dir`):**

  - **Step 1 (counting-phase feedback, FR-001a)**: First run's redirected
    log showed one `Counting documents... (page N)` line per page,
    `page 0` through `page 7` (8 listing pages), each appearing only
    after that page's rate-limited fetch completed — confirms the
    counting pass gives live, incremental feedback rather than staying
    silent during its own ~80s walk.
  - **Step 2 (bounded total before download starts, FR-001/SC-001)**:
    Both runs printed `Found 212 documents. Starting download.`
    immediately after the counting pass finished and before any
    `Progress:` line appeared — confirms the total is fully known and
    reported before the bounded phase begins.
  - **Step 3 (resilience across an interruption, FR-005)**: The first
    run was deliberately killed (`SIGTERM`) mid-download, after the
    counting phase and partway through downloading. Post-kill, the
    filesystem held exactly 6 PDFs and `manifest.json` held exactly 6
    entries — in sync, no orphaned files or dangling manifest rows.
    Confirms `download_category()`'s existing per-document commit
    behavior (feature 009's SC-004) is untouched by this feature's new
    callbacks.
  - **Step 4 (re-run detects already-downloaded documents as skipped,
    still advances progress, FR-003)**: The second run, invoked fresh
    against the same `--output-dir`, re-counted independently (again
    reporting `Found 212 documents` — confirms
    `count_documents_in_category()` doesn't depend on or get confused
    by partial prior state) and then processed all 212: its final
    summary read `Downloaded 206, skipped 6, failed 0` — the exact 6
    documents left over from the interrupted first run were correctly
    identified as already-downloaded and skipped, while still
    contributing to the reported progress total (skips call
    `on_progress` too, per data-model.md). `206 + 6 + 0 = 212`, matching
    the counted total exactly.
  - **Step 5 (redirected output stays readable, no control-code spam,
    SC-003/FR-006)**: Both log files, inspected after the fact,
    contained only plain readable text lines — no `\r` bytes, no ANSI
    escape sequences. `sys.stdout.reconfigure(line_buffering=True)` was
    separately confirmed live: killing the first run mid-flight still
    left its in-progress counting line correctly flushed to disk
    (previously reproduced as *empty* before this feature's fix — see
    research.md).
  - **Step 6 (throttled progress lines at 10%-boundaries, FR-002/SC-002)**:
    The second (uninterrupted) run's log contained exactly 10
    `Progress:` lines — `22/212 (10%)` through `212/212 (100%)`, one per
    decile crossing, none in between — confirming the throttling logic
    (already exhaustively unit-tested at `total=10` and `total=240` in
    `test_download_cli.py`) behaves identically against real timing and
    a real, non-round total.
  - **Step 7 (bar/count reaches the full total on completion, SC-001)**:
    Final summary line `Downloaded 206, skipped 6, failed 0` sums to
    212, matching both the counted total and the final `Progress:
    212/212 (100%)` line exactly. Final on-disk state (`ls *.pdf | wc -l`
    → 212, manifest entries → 212) matches too.
  - **Step 8 (immediate failure visibility, FR-002a)**: Not
    forced live — no real fetch failures occurred against the real
    site during either run, and quickstart.md itself notes this is
    "hard to force deterministically against the real site." Validated
    instead via the existing, passing unit tests that assert exact
    call ordering (`on_failure` before that document's `on_progress`
    call) and immediate (non-throttled) printing in both TTY
    (`tqdm.write`) and non-TTY (`print`) modes — `test_interactive_mode_on_failure_uses_tqdm_write_not_print`,
    `test_non_interactive_mode_prints_a_failure_line_immediately_regardless_of_throttling`.
  - Interactive (TTY) mode itself (bounded `tqdm` bar, indeterminate
    counting bar, `tqdm.write()` for failures) was not separately
    re-verified live in this pass, since it isn't reachable through a
    redirected/backgrounded shell command — it's covered by
    `test_download_cli.py`'s TTY-mode test group instead
    (T008/T009), which exercises the exact same `cli.py` code paths
    with `sys.stdout.isatty` mocked `True`.
  - Test artifacts (`/tmp/qs-progress-bar/`, log files) cleaned up
    after validation.
- [X] T013 Run the full backend test suite (`pytest`), confirm no
  regressions in previously-passing tests (Constitution's CI
  requirement), and re-confirm this project's established CI-parity
  discipline: the backend unit suite still passes with no `.env`/env
  vars at all — including a fresh check that importing `download/cli.py`
  (the first module in this project to import `tqdm`) introduces no
  new import-time issue

  **Results:**
  - Full suite: `332 passed` (no regressions).
  - No-`.env` CI-parity check (`.env` moved aside, `env -i` with only
    `PATH`/`HOME`): `import src.modules.download.cli` succeeds — `tqdm`
    introduces no import-time dependency on settings/env vars — and the
    full unit suite (`tests/unit`) still passes: `264 passed`. `.env`
    restored afterward.
- [X] T014 Bump `VERSION`/`frontend/package.json`/`backend/src/__init__.py`
  and add a linked `CHANGELOG.md` entry, per the constitution's
  Development Workflow rule

  **Results**: All three bumped `0.13.0` → `0.14.0`; `CHANGELOG.md`
  entry added under `[0.14.0] - 2026-08-11`, linked to
  `specs/015-download-progress-bar/spec.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001's `tqdm` install,
  needed before any rendering code is written, though not by
  `service.py` itself — `service.py` never imports `tqdm`, per
  research.md/plan.md's service-vs-rendering split) — BLOCKS both user
  stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion
  and on `cli.py`'s `isatty()`-dispatch structure already existing
  (T009), since it adds the other branch to that same dispatch rather
  than creating it from scratch
- **Polish (Phase 5)**: Depends on both user stories being complete

### Within Each User Story

- Tests MUST be written and confirmed failing before their
  corresponding implementation task (Constitution Principle I)
- Foundational callbacks (Phase 2) before either rendering mode, since
  both modes are just different ways of consuming the same hooks
- Backend-only feature — no frontend involvement at any point

---

## Parallel Example: Foundational Phase

```bash
# These extend the same test file but are independent additions,
# writable together:
Task: "Write failing tests for count_documents_in_category() in backend/tests/unit/test_download_service.py"
Task: "Write failing tests for download_category()'s on_progress parameter in backend/tests/unit/test_download_service.py"
Task: "Write failing tests for download_category()'s on_failure parameter in backend/tests/unit/test_download_service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks both stories)
3. Complete Phase 3: User Story 1 (interactive rendering)
4. **STOP and VALIDATE**: Run the CLI in a real terminal, confirm
   counting feedback and a bounded bar both work end-to-end
5. Deploy/demo if ready — the interactive experience is already the
   primary, P1 use case

### Incremental Delivery

1. Complete Setup + Foundational → progress can be computed and
   reported, nothing renders it yet
2. Add User Story 1 → interactive terminal experience works → validate
3. Add User Story 2 → redirected/logged runs stay readable → validate
4. Each story adds value without breaking the previous one

---

## Notes

- [P] tasks = different files, or independent additions to the same
  file with no ordering dependency between them
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing
- Commit after each task or logical group, split by conventional type
  (feat/test/chore), per this session's established pattern
- Stop at any checkpoint to validate a story independently
