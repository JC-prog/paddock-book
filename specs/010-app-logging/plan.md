# Implementation Plan: Application Logging

**Branch**: `010-app-logging` | **Date**: 2026-08-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-app-logging/spec.md`

## Summary

Adds structured, JSON-formatted backend logging: every request is logged
with a unique correlation ID, method, path, status, and duration; unhandled
errors are logged with enough detail to diagnose without reproducing;
authentication events (login success/failure, logout, registration) and
chat requests (account + department retrieved) are logged as explicit
business events. No question/answer text, passwords, or tokens are ever
logged. All of it goes to stdout — no new external logging service.

## Technical Context

**Language/Version**: Python 3.12 (matches the rest of `backend/`)

**Primary Dependencies**: None new — Python's standard-library `logging`
module plus a small hand-rolled JSON `Formatter` (~20 lines); no
third-party logging library needed for this scope, and Starlette's
`BaseHTTPMiddleware` (already available via FastAPI) for the request-level
middleware

**Storage**: None — logs are written to stdout only, no database or file
storage. Per spec.md's Assumptions, where they end up retained (e.g.
CloudWatch under the AWS Lambda/Fargate deployment target) is an
operational concern outside this feature's scope

**Testing**: pytest, using its built-in `caplog` fixture to assert on
emitted log records — no live external logging service to isolate,
consistent with Constitution Principle II

**Target Platform**: Same as the rest of the backend — runs as part of the
FastAPI app process

**Project Type**: Backend-only addition to the existing `backend/`
codebase (FR-009 — frontend explicitly out of scope)

**Performance Goals**: None beyond not meaningfully slowing requests down
— logging must stay cheap enough to run on every request unconditionally

**Constraints**: MUST NOT log passwords, tokens, or chat question/answer
text under any circumstance (FR-006, FR-008); MUST NOT let a logging
failure fail a request (FR-007)

**Scale/Scope**: Every backend request and every auth/chat event, for as
long as the process runs — no sampling or rate-limiting of what gets
logged

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Test-First Development**: Applies as normal — the JSON formatter,
  the request-ID context propagation, the request-logging middleware, and
  each auth/chat event log call all get a failing test first in
  `tasks.md`. PASS.
- **II. Comprehensive Unit Testing**: Fully unit-testable via `caplog` —
  no live external service (no log shipping/aggregation is part of this
  feature's scope), so nothing here needs integration-test isolation.
  PASS.
- **III. API Contract Consistency**: This feature adds no new HTTP
  endpoint and changes no existing request/response shape or status code
  — logging is purely an internal side effect of handling a request, not
  part of what a client observes. The JSON log record's own shape is
  documented as a contract in `contracts/log-schema.md` since other
  tooling may eventually parse it, even though it isn't an API contract
  in Principle III's sense. PASS.
- **IV. Clean Code & Readability**: Applies as normal. PASS.
- **V. Separation of Concerns**: The shared logging infrastructure
  (formatter, request-ID propagation, request-logging middleware) lives
  in `core/`, matching the constitution's explicit statement that `core/`
  holds cross-cutting middleware. Auth-event and chat-event log calls
  live inside `modules/auth/service.py` and `modules/chat/router.py`
  respectively — the modules that already own those business events —
  rather than a new module reaching into their internals. PASS.

No violations — Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/010-app-logging/
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
├── src/
│   ├── core/
│   │   ├── logging.py       # NEW — JsonFormatter, request_id_var (ContextVar), configure_logging()
│   │   └── middleware.py    # NEW — RequestLoggingMiddleware (FR-001, FR-002, FR-003, FR-007)
│   ├── main.py               # MODIFIED — calls configure_logging(), registers RequestLoggingMiddleware
│   └── modules/
│       ├── auth/
│       │   └── service.py    # MODIFIED — login/logout/register log their event (FR-004, FR-006)
│       └── chat/
│           └── router.py     # MODIFIED — post_chat logs account + department on successful retrieval (FR-005, FR-008)
└── tests/
    └── unit/
        ├── test_core_logging.py       # NEW
        ├── test_core_middleware.py    # NEW
        ├── test_auth_service.py       # MODIFIED — adds log-emission assertions
        └── test_chat.py               # MODIFIED — adds log-emission assertions
```

**Structure Decision**: Backend-only. Shared logging plumbing is new
`core/` modules (matching the constitution's stated home for
cross-cutting middleware); event-specific log calls are added directly
inside the existing `auth`/`chat` modules that already own those events,
not centralized into a new logging-specific module — keeping each
module's business events logged where they actually happen.

## Complexity Tracking

*No violations — table intentionally omitted.*
