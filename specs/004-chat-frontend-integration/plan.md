# Implementation Plan: Chat Frontend-Backend Integration

**Branch**: `004-chat-frontend-integration` | **Date**: 2026-08-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-chat-frontend-integration/spec.md`

## Summary

Wire the existing chat UI (feature 002) to the existing `/v1/chat` streaming
address (feature 003): sending a message now calls the backend and renders
its reply as a second, visually distinct bubble that grows incrementally as
words arrive, fails visibly after a 10-second silence or a dropped
connection, and blocks further sends until that reply settles. Split the new
HTTP/SSE transport logic into its own service, separate from the existing
message-list state service, per the user's explicit separation-of-concerns
requirement and Constitution Principle V. The only backend change is
widening CORS to allow `POST` from the frontend origin — the `/v1/chat`
contract itself (feature 003) is unchanged.

## Technical Context

**Language/Version**: TypeScript 5.x (Angular 18, frontend); Python 3.12
(backend — CORS config only, no new backend logic)

**Primary Dependencies**: No new packages. Frontend uses the browser's
native `fetch` + `ReadableStream` (already how research.md for feature 003
anticipated a real client would consume the SSE contract, since `EventSource`
can't POST). Backend reuses the existing `CORSMiddleware`.

**Storage**: N/A — still no persistence; each message/reply pair is
independent and stateless (spec Assumptions)

**Testing**: Vitest (frontend) with a mocked global `fetch` returning a
constructed `ReadableStream`, so the SSE parsing/timeout/error logic is
tested with no real network call; pytest (backend) for the CORS
configuration change

**Target Platform**: Unchanged — same frontend dev server and backend ASGI
process as prior features

**Project Type**: Full-stack (Option 2) — frontend `features/chat/` changes
plus one backend config line

**Performance Goals**: A reply begins appearing within 2 seconds of sending
(SC-001)

**Constraints**: A message is treated as failed if no part of its reply
arrives within 10 seconds (FR-005, SC-003); only one message may be
in-flight at a time — sending is blocked until the current reply completes
or fails (FR-007); the backend must accept cross-origin `POST` requests from
the frontend for `/v1/chat` (Assumptions)

**Scale/Scope**: One existing entity (`ChatMessage`) extended with two new
fields; one new frontend service; no new backend endpoints or entities

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature | Status |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Yes — failing tests for the new `ChatApiService` (mocked fetch/SSE parsing, timeout, error), the extended `ChatService` (orchestration, `isSending`), `ChatInputComponent` (disabled-while-sending), and `MessageBubbleComponent` (per-sender/status styling) must exist before their implementations change | PASS (enforced at task-generation/implementation time) |
| II. Comprehensive Unit Testing | Yes — `ChatApiService` is tested against a mocked `fetch`/`ReadableStream`, never a real network call; `ChatService` is tested against a mocked `ChatApiService`, matching the existing pattern already used for `HealthService`/`ChatService` in prior features | PASS |
| III. API Contract Consistency | Yes — this feature consumes the existing `/v1/chat` contract (`specs/003-chat-api-sse/contracts/chat-api.md`) unchanged; only the CORS policy widens to permit the request, which is not a contract shape change | PASS |
| IV. Clean Code & Readability | Yes — transport (`ChatApiService`) and state/orchestration (`ChatService`) are kept as separate, single-responsibility files rather than one growing service | PASS |
| V. Separation of Concerns | Yes — directly the point of this plan's structure: transport layer, state/orchestration layer, and presentation (components) remain distinct, per the user's explicit requirement and the amended Principle V | PASS |

No violations. Complexity Tracking is not needed.

**Post-Phase 1 re-check**: `data-model.md` (two new `ChatMessage` fields
plus one new `ChatService` field), `contracts/cors-policy.md` (a one-line
CORS widening, no new endpoints), and `quickstart.md` introduce nothing
beyond what Phase 0 research already accounted for. All five principles
still PASS; no new complexity, dependency, or scope was added during
design.

## Project Structure

### Documentation (this feature)

```text
specs/004-chat-frontend-integration/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
frontend/
└── src/app/features/chat/
    ├── chat-message.model.ts         # modified — add `sender` and `status` fields
    ├── chat-api.service.ts            # new — fetch + SSE parsing, timeout, error handling; returns an Observable<string> of words
    ├── chat-api.service.spec.ts       # new
    ├── chat.service.ts                # modified — orchestrates ChatApiService + message list, exposes isSending
    ├── chat.service.spec.ts           # modified
    ├── chat-input.component.ts        # modified — disable send while isSending()
    ├── chat-input.component.spec.ts   # modified
    ├── message-bubble.component.ts    # modified — style by sender/status
    ├── message-bubble.component.spec.ts # modified
    ├── chat-box.component.ts          # unchanged — still just renders whatever messages() provides
    └── chat-page.component.ts         # unchanged

backend/
└── src/main.py                        # modified — CORS allow_methods adds "POST"
```

**Structure Decision**: Stays within the existing `features/chat/` module
(Constitution Principle V) — this is an extension of feature 002/003, not a
new domain. The key structural decision is splitting `ChatApiService`
(transport: owns `fetch`, SSE line parsing, the 10-second timeout, and error
translation) from `ChatService` (orchestration: owns the message list signal,
decides when to append/update/finalize a message, exposes `isSending` for
`ChatInputComponent` to bind against). Components never touch `fetch`
directly, and `ChatApiService` never touches the message list — each layer
has exactly one reason to change, directly satisfying the user's
separation-of-concerns requirement.

## Complexity Tracking

*Not applicable — the Constitution Check above has no violations to justify.*
