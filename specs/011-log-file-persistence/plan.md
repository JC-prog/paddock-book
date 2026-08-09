# Implementation Plan: Log File Persistence

**Branch**: `011-log-file-persistence` | **Date**: 2026-08-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-log-file-persistence/spec.md`

## Summary

Extends feature 010's `configure_logging()` to optionally also write every
log entry to a size-rotated file on disk, reusing the same `JsonFormatter`
so file content matches stdout exactly. File persistence is a `Settings`
flag (default on), so a future admin panel has a concrete, existing toggle
to drive rather than needing to build this mechanism. Rotation is size-based
with a fixed number of backups — a hard, predictable cap on total disk
usage regardless of traffic volume — and any failure to set up the file
destination degrades to stdout-only logging rather than blocking app
startup or failing requests.

## Technical Context

**Language/Version**: Python 3.12 (matches the rest of `backend/`)

**Primary Dependencies**: None new — `logging.handlers.RotatingFileHandler`
is part of the standard library and already does exactly what FR-003/
FR-004 need (size-based rollover, a fixed `backupCount` of retained files)

**Storage**: Local filesystem — a rotating set of log files under
`logs/` (relative to wherever the backend process is started, typically
`backend/`), gitignored; not a database

**Testing**: pytest, writing to `tmp_path` — no live external service to
isolate, consistent with Constitution Principle II. One test actually
drives real rollover with a tiny `maxBytes` threshold rather than only
asserting on `RotatingFileHandler`'s configuration

**Target Platform**: Same as feature 010 — part of the FastAPI app process

**Project Type**: Backend-only addition to the existing `backend/`
codebase (spec.md's Assumptions explicitly keep the AWS/CloudWatch path
and the future admin panel out of scope)

**Performance Goals**: None beyond not meaningfully slowing requests down
— same bar as feature 010

**Constraints**: MUST NOT change feature 010's log content/format; MUST
NOT let a broken file destination block app startup or fail a request
(FR-005); MUST keep total log-file disk usage capped and predictable
(FR-004)

**Scale/Scope**: One rotating file set per running backend process; no
change to log volume/content, only where it additionally goes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Test-First Development**: Applies as normal — `tasks.md` writes a
  failing test for every behavior (flag on/off, rollover, graceful
  degradation) before its implementation. PASS.
- **II. Comprehensive Unit Testing**: Fully unit-testable against
  `tmp_path` — no live external service involved. PASS.
- **III. API Contract Consistency**: Not applicable — no new endpoint, no
  request/response change. The log record shape itself is unchanged from
  feature 010's `contracts/log-schema.md`, which this feature doesn't
  touch. PASS.
- **IV. Clean Code & Readability**: Applies as normal. PASS.
- **V. Separation of Concerns**: All changes stay inside `core/`
  (`config.py`, `logging.py`) — the same cross-cutting home feature 010
  already established. No other module is touched. PASS.

No violations — Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/011-log-file-persistence/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `contracts/` directory — this feature adds no new external interface
(no endpoint, no CLI, no changed file format); feature 010's
`contracts/log-schema.md` already covers the log record shape, unchanged
here.

### Source Code (repository root)

```text
backend/
├── src/
│   └── core/
│       ├── config.py     # MODIFIED — 4 new Settings fields (log_to_file, log_file_path, log_file_max_bytes, log_file_backup_count)
│       └── logging.py    # MODIFIED — configure_logging() optionally attaches a RotatingFileHandler
└── tests/
    └── unit/
        └── test_core_logging.py   # MODIFIED — adds file-persistence tests

.gitignore                 # MODIFIED — ignore the log output directory
```

**Structure Decision**: No new module — this is a small, self-contained
extension of feature 010's existing `core/logging.py` and `core/config.py`,
matching the constitution's "cross-cutting concerns live in `core/`"
convention exactly. No frontend involvement.

## Complexity Tracking

*No violations — table intentionally omitted.*
