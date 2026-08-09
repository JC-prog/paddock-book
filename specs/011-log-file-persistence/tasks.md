---

description: "Task list for feature implementation"
---

# Tasks: Log File Persistence

**Input**: Design documents from `/specs/011-log-file-persistence/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Tests**: Required (not optional) — Constitution Principle I (Test-First
Development) is NON-NEGOTIABLE for this project: every implementation task
below has a corresponding test task that MUST be written first, confirmed
failing, then made to pass.

**Organization**: Tasks are grouped by user story (US1, US2) per spec.md's
priorities.

## Path Conventions

Backend-only feature: `backend/src/core/config.py`,
`backend/src/core/logging.py`, `backend/tests/unit/test_core_logging.py`,
repository-root `.gitignore`.

---

## Phase 1: Setup

**Purpose**: Configuration surface this feature needs

- [X] T001 Add `log_to_file: bool = True`, `log_file_path: str =
  "logs/app.log"`, `log_file_max_bytes: int = 10 * 1024 * 1024`,
  `log_file_backup_count: int = 5` to `Settings` in
  `backend/src/core/config.py` (per data-model.md)
- [X] T002 [P] Add `backend/logs/` to the repository root `.gitignore` —
  the existing bare `*.log` pattern covers `app.log` itself but not
  rotated backups like `app.log.1` (research.md)

---

## Phase 2: User Story 1 - Open a real log file after the fact (Priority: P1) 🎯 MVP

**Goal**: With file persistence enabled (the default), every log entry
also lands in a real file on disk, in the same JSON shape as stdout; with
it disabled, no file is created at all; a broken file destination never
blocks app startup.

**Independent Test**: Run the app, trigger a request, confirm the entry
appears in the configured log file — readable after the process stops —
and confirm toggling the setting off produces no file at all (per
spec.md's US1 acceptance scenarios).

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T003 [P] [US1] Write failing tests for file-persistence in
  `backend/tests/unit/test_core_logging.py` — cover: with
  `log_to_file=True` (via an injected fake settings object), a
  `RotatingFileHandler` is attached to the root logger, pointed at the
  configured path, with the configured `maxBytes`/`backupCount`, and
  using the same `JsonFormatter` as the stdout handler; a log call after
  configuring actually writes a matching JSON line to a real file under
  `tmp_path` (not mocked); with `log_to_file=False`, no file handler is
  attached and no file or directory is created; a non-existent log
  directory is created automatically on first configure; when the
  directory can't be created or written (point `log_file_path` somewhere
  unwritable), `configure_logging()` does not raise, the stdout handler
  is still attached, and one `WARNING`-level line is emitted noting the
  failure (FR-005)
- [X] T004 [US1] Implement `_try_build_file_handler()` and extend
  `configure_logging(level=..., *, settings_factory=Settings)` in
  `backend/src/core/logging.py` to make T003 pass (depends on T001, T003)

**Checkpoint**: User Story 1 is fully functional and independently
testable — SC-001 and SC-002 hold, and FR-005's degradation guarantee is
proven by a real test, not assumed.

---

## Phase 3: User Story 2 - Log files never grow without bound (Priority: P2)

**Goal**: Once the active log file reaches the configured size, it rolls
over automatically, and total disk usage across all log files never
exceeds a fixed cap.

**Independent Test**: Configure a small size threshold, produce enough
log volume to roll over multiple times, and confirm the file count and
total size both stay within the configured bounds (per spec.md's US2
acceptance scenarios).

**Note**: Unlike most story pairs in this project, US2 needs no
*additional* implementation beyond US1's — `RotatingFileHandler` (stdlib)
already performs rollover and pruning on its own once configured (T004),
per research.md's decision. US2 is entirely a test-and-verify story on
top of US1's existing code; it depends on T004 being complete, not just
on Setup.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST — they should already pass once T004
> exists, since `RotatingFileHandler` provides this behavior; if any
> fails, that's a real bug in how T004 wired it up, not missing code to
> write here.**

- [X] T005 [P] [US2] Write tests proving rotation and the disk-usage cap
  in `backend/tests/unit/test_core_logging.py` — cover: configuring with
  a small `log_file_max_bytes` (via the injected fake settings) and
  writing enough real log entries causes `app.log` to roll over into
  `app.log.1`; writing enough further volume to exceed
  `log_file_backup_count` results in at most `backup_count + 1` files
  ever existing under `tmp_path`, with the oldest pruned automatically;
  total bytes across all files never exceeds
  `max_bytes * (backup_count + 1)` (depends on T004) — all 3 tests passed
  immediately as expected. While verifying this, re-ran the no-`.env`
  CI-parity check on `import src.main` directly (not just `pytest`) and
  found a real regression: `configure_logging()`'s `settings_factory()`
  call itself wasn't protected, so a real `Settings()` at import time
  (missing `database_url`/`jwt_secret` in CI) would have crashed app
  startup entirely. Added a dedicated regression test
  (`test_configure_logging_falls_back_to_stdout_only_when_settings_cannot_be_read`)
  and fixed it — see research.md's "Real regression caught by the
  no-`.env` CI-parity check" note.

**Checkpoint**: User Stories 1 AND 2 both fully functional — SC-003 holds,
verified by actually triggering rollover, not just asserting
configuration values.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Final validation against a running backend and full-suite
regression check

- [X] T006 [P] Run the full `quickstart.md` validation against a locally
  running backend and confirm FR-001–FR-005 / SC-001–SC-004, documenting
  results in this tasks.md file — Ran the real backend against real
  Postgres. Step 1: `GET /health` produced a real `logs/app.log` whose
  last line matched stdout exactly — SC-001 confirmed live. Step 2:
  stopped the process, file remained fully readable — SC-002 confirmed
  live. Step 3: set `LOG_TO_FILE=false`, restarted — no `logs/` directory
  created at all, app served normally — FR-002 confirmed live. Step 4:
  set `LOG_FILE_MAX_BYTES=2048`, generated 240+ real requests — file
  count stayed at exactly 6 (`app.log` + 5 backups) throughout, oldest
  data pruned automatically, total bytes (~11.4 KB) well within the
  12 KB cap — SC-003 confirmed live, not just via unit tests. Step 5: set
  `LOG_FILE_PATH=/root/unwritable/app.log`, restarted — app still started
  and served `GET /health` (200), no file created, and a `WARNING`-level
  `log_file_setup_failed` line named the exact broken path — SC-004
  confirmed live. `.env` restored to its pre-test state afterward.
- [X] T007 Run the full backend test suite (`pytest`) and confirm no
  regressions in previously-passing tests, including the no-`.env`
  CI-parity check this project adopted after an earlier CI failure
  (Constitution's CI requirement) — 186/186 passed (unit + integration).
  Re-ran the unit suite with no `.env`/env vars at all: 145/145 passed —
  this check is what caught the real `configure_logging()` import-time
  regression documented under T005/research.md; without it, this feature
  would have broken CI entirely for every test importing `src.main`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **User Story 1 (Phase 2)**: Depends on Setup (T001's new Settings
  fields)
- **User Story 2 (Phase 3)**: Depends on User Story 1's implementation
  (T004) being complete — not just Setup, since there's no separate US2
  implementation (see the Note above)
- **Polish (Phase 4)**: Depends on both user stories being complete

### Within Each User Story

- Tests MUST be written and confirmed failing before their corresponding
  implementation task (Constitution Principle I) — T005 is the one
  exception in spirit: it's expected to pass immediately against T004's
  existing implementation, since stdlib `RotatingFileHandler` already
  provides the behavior being verified

### Parallel Opportunities

- T001 and T002 (Setup, different files) can run in parallel
- T006 and T007 (Polish) can run in parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: User Story 1
3. **STOP and VALIDATE**: logs now persist to a real, toggleable file
   with graceful degradation — already the feature's core value
4. User Story 2 (rotation) is what makes it safe to leave running
   long-term, but US1 alone is already useful for a single debugging
   session

### Incremental Delivery

1. Setup → configuration surface ready
2. Add User Story 1 → real file persistence, toggleable, degrades
   gracefully → already shippable
3. Add User Story 2 → verified rotation/disk cap → ship
4. Polish → full live validation + regression check

## Notes

- [P] tasks = different files, no dependencies on each other
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group, split by conventional commit
  type (test:/feat:/chore:), per this project's established convention
- Verify each test fails before implementing the code that makes it pass
  (except T005, per the Note in Phase 3)
