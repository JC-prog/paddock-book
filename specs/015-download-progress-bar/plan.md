# Implementation Plan: Download CLI Progress Bar

**Branch**: `015-download-progress-bar` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-download-progress-bar/spec.md`

## Summary

Adds real-time progress feedback to `modules/download/cli.py`: a new
counting pass (`count_documents_in_category()`) walks every listing
page once, purely to establish a true total, before the existing
`download_category()` download pass begins unchanged; `download_category()`
gains optional, backward-compatible `on_progress`/`on_failure` callback
hooks so the CLI can render a live bounded bar without altering the
function's actual download/skip/failure behavior at all. Rendering
itself branches on whether stdout is a real terminal — an interactive
TTY gets a live `tqdm` bar, redirected/piped output gets plain,
throttled, newline-terminated status lines — a distinction discovered
to be necessary by testing `tqdm`'s actual behavior directly (see
research.md), not assumed.

## Technical Context

**Language/Version**: Python 3.12 (backend — same as the rest of the repo)

**Primary Dependencies**: `tqdm` (new — user's explicit choice per the
pre-specify planning discussion) for the interactive progress bar; no
other new dependency

**Storage**: N/A — this feature adds no persistent state; it only adds
visibility into `modules/download/`'s existing manifest-file-based
download process (feature 009), unchanged

**Testing**: pytest — unit tests for `count_documents_in_category()`
and `download_category()`'s new callback hooks (both already
fully mockable via this module's existing `fetch_page`/`fetch_pdf`/
`listing`/`rate_limiter` DI parameters); unit tests for the CLI's
TTY-vs-non-TTY rendering choice with `sys.stdout.isatty` mocked

**Target Platform**: Same backend as every other feature — this is an
operator-run CLI enhancement within it, not a new service

**Project Type**: CLI enhancement (matches `modules/download/`'s
existing shape — no new module)

**Performance Goals**: The counting pass adds one extra rate-limited
walk of listing pages only (not PDF downloads) — roughly 80 seconds
for an 8-page category, a small fraction of a ~40-minute full run
(spec.md Assumptions)

**Constraints**: MUST NOT change which documents are downloaded,
skipped, or treated as failed (FR-004); MUST preserve the existing
guarantee that documents downloaded before a later failure remain
intact (FR-005) — the counting pass MUST stay separate from the
download pass, not merged into a single collect-then-download flow;
MUST produce genuinely readable, non-corrupted output when redirected
to a file, not just avoid corruption via silence (FR-006 — see
research.md's finding that naive `tqdm` usage fails this)

**Scale/Scope**: One existing file gains optional callback parameters
(`download/service.py`), one new function in the same file
(`count_documents_in_category()`), one CLI file gains rendering logic
(`download/cli.py`) — no new module, no new persistent state

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Test-First Development**: Applies as normal — every new
  function/callback/branch gets a failing test first in `tasks.md`.
  PASS.
- **II. Comprehensive Unit Testing**: `count_documents_in_category()`
  and `download_category()`'s new callbacks are unit-tested with
  `fetch_page`/`listing`/`rate_limiter` mocked, matching this module's
  existing test style (`tests/unit/test_download_service.py`) — no
  test touches the real network or filesystem beyond what's already
  mocked today. PASS.
- **III. API Contract Consistency**: N/A — no HTTP API surface exists
  or changes here; the "contract" is the CLI's observable output shape,
  documented in `contracts/cli-output.md`. PASS.
- **IV. Clean Code & Readability**: Applies as normal. PASS.
- **V. Separation of Concerns**: No new module boundary — this is a
  same-module enhancement (`modules/download/`), consistent with the
  constitution's module-shape rule (nothing here reaches across a
  boundary; `cli.py` already depends on `service.py` today). PASS.

No Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/015-download-progress-bar/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── requirements.txt            # MODIFIED — adds tqdm
├── src/modules/download/
│   ├── service.py               # MODIFIED — count_documents_in_category() (new),
│   │                             #   download_category() gains on_progress/on_failure
│   │                             #   callback params (both default None, backward compatible)
│   └── cli.py                    # MODIFIED — counting phase + TTY-aware progress rendering
└── tests/unit/
    ├── test_download_service.py  # MODIFIED — new tests for the above
    └── test_download_cli.py      # NEW — rendering-mode selection, isatty mocked
```

**Structure Decision**: Same-module enhancement to the existing
`modules/download/` — no new module, no new API surface, no frontend
changes. `service.py` stays the single source of truth for download
behavior; `cli.py` stays the only place that knows how to *render*
progress, matching the existing separation between the two files.

## Complexity Tracking

*No violations — table intentionally omitted.*
