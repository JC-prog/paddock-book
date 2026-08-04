# Implementation Plan: Chat API with Streamed Responses

**Branch**: `003-chat-api-sse` | **Date**: 2026-08-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-chat-api-sse/spec.md`

## Summary

Add a backend-only `POST /v1/chat` address that accepts `{"message": string}`,
rejects empty/whitespace-only messages, and streams back a fixed placeholder
reply ("Hello, this is a test response.") as Server-Sent Events — one word per
event — closing the connection once the full reply has been sent. No frontend
wiring, no persistence, no real response generation; this proves the streaming
plumbing per spec.md FR-001–FR-007 and SC-001–SC-005.

## Technical Context

**Language/Version**: Python 3.12 (unchanged from features 001/002)

**Primary Dependencies**: FastAPI (existing); `sse-starlette` 2.4.1 (new) for
spec-compliant SSE framing and client-disconnect detection

**Storage**: N/A — stateless, single-turn, nothing persisted (spec Key
Entities, Assumptions)

**Testing**: pytest + `httpx`'s streaming `Client.stream()` (via FastAPI's
`TestClient`), to read the SSE response incrementally rather than buffering
the whole body

**Target Platform**: Same backend ASGI process as features 001/002; no new
deployment target

**Project Type**: Backend-only change (frontend untouched, per spec
Assumptions — no Option 2 split needed this time)

**Performance Goals**: Streaming begins within 1 second of a valid request
(SC-001)

**Constraints**: No authentication (FR-006); each request handled
independently with no shared state (FR-007); reply delivered as multiple
discrete word-level events, never as one single event (FR-004, SC-005)

**Scale/Scope**: Single new address, no concurrency limits specified, no
persistence layer

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature | Status |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Yes — a failing test for message validation, event count, completion signal, and disconnect handling must exist before the router/service code | PASS (enforced at task-generation/implementation time) |
| II. Comprehensive Unit Testing | Yes — tests exercise the SSE stream via `httpx`'s streaming client, with no live LLM or external dependency to fake (none exists yet) | PASS |
| III. API Contract Consistency | Yes — the request body shape and SSE event format are defined as an explicit contract (`contracts/chat-api.md`) rather than left implicit; any change to either requires updating the contract and its tests together | PASS |
| IV. Clean Code & Readability | Yes — router (HTTP/SSE plumbing) and a small placeholder-reply generator are separate, single-responsibility pieces; no speculative abstraction (no repository/service layer beyond what a placeholder needs) | PASS |
| V. Separation of Concerns | Yes — new `modules/chat/` (router, schemas, service) mirrors the existing `modules/health/` convention from the amended Principle V | PASS |

No violations. Complexity Tracking is not needed.

**Post-Phase 1 re-check**: `data-model.md` (two transient, unpersisted
shapes), `contracts/chat-api.md` (request/reply/rejection/disconnect
contract), and `quickstart.md` introduce nothing beyond a single
unauthenticated streamed endpoint. All five principles still PASS; no new
complexity, dependency beyond `sse-starlette`, or scope was added during
design.

## Project Structure

### Documentation (this feature)

```text
specs/003-chat-api-sse/
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
│   ├── main.py                  # modified — mount the chat router
│   └── modules/
│       ├── health/               # existing (feature 001), unchanged
│       └── chat/                 # new
│           ├── __init__.py
│           ├── router.py         # POST /v1/chat — SSE endpoint
│           ├── schemas.py        # ChatRequest (message: str)
│           └── service.py        # placeholder word-by-word reply generator
└── tests/
    └── unit/
        └── test_chat.py          # new

frontend/                          # untouched by this feature
```

**Structure Decision**: Backend-only, following the existing `modules/<name>/`
convention from the amended Constitution Principle V. `chat/router.py` owns
HTTP/SSE request handling; `chat/service.py` owns generating the placeholder
word sequence (kept separate so the streaming/HTTP concern and the
reply-generation concern can be tested and later replaced independently — the
generation logic is exactly what a future feature will swap for a real
language-model call). No `schemas.py` split for the reply shape is needed
beyond the request (`ChatRequest`) — the SSE events themselves are plain text
words per `contracts/chat-api.md`, not a JSON response body needing its own
Pydantic model.

## Complexity Tracking

*Not applicable — the Constitution Check above has no violations to justify.*
