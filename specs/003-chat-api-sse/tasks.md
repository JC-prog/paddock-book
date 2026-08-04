---

description: "Task list for Chat API with Streamed Responses"
---

# Tasks: Chat API with Streamed Responses

**Input**: Design documents from `/specs/003-chat-api-sse/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/chat-api.md, quickstart.md

**Tests**: Included and required — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates a failing test before implementation for every requirement in this feature.

**Organization**: This feature has a single user story (P1). All backend tasks carry the `[US1]` label; there is no frontend work (spec.md Assumptions — out of scope).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 — the only story in this feature)
- Paths below are all under `backend/` per plan.md Project Structure

---

## Phase 1: Setup

**Purpose**: Add the new dependency and scaffold the `chat` module directory

- [X] T001 [P] Add `sse-starlette==3.4.6` to `backend/requirements.txt` — corrected to `2.4.1` during implementation: 3.4.6 requires `starlette>=0.49.1`, which conflicts with `fastapi==0.115.6`'s pinned `starlette<0.42.0`; 2.4.1 has no hard `starlette` pin and installs cleanly (`pip check` passes)
- [X] T002 [P] Create the `backend/src/modules/chat/` package (`__init__.py`), per the existing `modules/health/` convention

**Checkpoint**: `chat` module directory exists and `sse-starlette` is an installable dependency. No shared/foundational infrastructure beyond this is needed — this feature has only one story, and `main.py`'s app instance and CORS middleware already exist from feature 001.

---

## Phase 2: User Story 1 - Send a message and receive a streamed reply (Priority: P1) 🎯 MVP

**Goal**: `POST /v1/chat` accepts a message, rejects empty/whitespace-only input, and streams back the fixed placeholder reply as multiple word-level SSE events, closing the connection when done (spec.md User Story 1).

**Independent Test**: Send a message to `/v1/chat` and confirm a streamed response arrives as multiple discrete events and completes — fully verifiable with no real response-generation logic behind it.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (Constitution Principle I)**

- [X] T003 [US1] Write failing tests for `POST /v1/chat` in `backend/tests/unit/test_chat.py`, covering: a valid message streams the placeholder as multiple discrete word events in order and the connection then closes (FR-003, FR-004, FR-005, SC-002, SC-004, SC-005); an empty or whitespace-only message is rejected with no events produced (FR-002, SC-003); a mid-stream client disconnect does not raise an unhandled server-side error (Acceptance Scenario 5) — includes an autouse fixture resetting `sse_starlette.sse.AppStatus.should_exit_event`, a known cross-test-event-loop issue in the library

### Implementation for User Story 1

- [X] T004 [P] [US1] Implement the `ChatRequest` schema (`message: str`, rejecting empty/whitespace-only via validation) in `backend/src/modules/chat/schemas.py` per data-model.md
- [X] T005 [P] [US1] Implement a generator yielding the fixed placeholder ("Hello, this is a test response.") one word at a time in `backend/src/modules/chat/service.py` per research.md
- [X] T006 [US1] Implement the `POST /v1/chat` route using `sse-starlette`'s `EventSourceResponse` wrapping the service generator, validated against `ChatRequest`, per `contracts/chat-api.md` — in `backend/src/modules/chat/router.py` (depends on T004, T005) — makes T003 pass
- [X] T007 [US1] Mount the chat router into the FastAPI app in `backend/src/main.py` (depends on T006)
- [X] T008 [US1] Manually validate Acceptance Scenarios 1–5 via quickstart.md steps 2–4 (depends on T007) — verified via curl against a running dev server: valid message streams 6 discrete `data:` lines matching "Hello, this is a test response." (Scenarios 1–3), empty/whitespace message returns 422 with no events (Scenario 4). Scenario 5 (disconnect) was inconclusive via curl since the local response completes faster than curl's timeout can trigger; the automated test (T003) deterministically forces an early close and passed, which is the real coverage for this scenario

**Checkpoint**: At this point, User Story 1 is fully functional and independently testable — this is the entire MVP for this feature.

---

## Phase 3: Polish & Cross-Cutting Concerns

**Purpose**: Final validation

- [X] T009 Run full quickstart.md validation (backend `pytest`, plus all manual scenarios from steps 2–4) and confirm SC-001–SC-005 are met (depends on T008) — final `pytest` run: 7/7 passing (4 new chat tests + 3 existing health tests)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **User Story 1 (Phase 2)**: Depends on Setup completion (needs `sse-starlette` installed and the `chat/` package to exist)
- **Polish (Phase 3)**: Depends on User Story 1 completion

### Within User Story 1

- Test (T003) MUST be written and FAIL before its corresponding implementation tasks (Constitution Principle I)
- `ChatRequest` schema (T004) and the placeholder generator (T005) are independent of each other
- Both T004 and T005 before the router that uses them (T006)
- Router (T006) before mounting it (T007)
- Implementation complete (T007) before manual scenario validation (T008)

### Parallel Opportunities

- T001 and T002 (Setup) can run in parallel — different files
- T004 and T005 (US1 implementation) can run in parallel — different files, no dependency between the request schema and the placeholder generator

---

## Parallel Example: User Story 1

```bash
# Once T003 (tests) exists and fails, these two can proceed together:
Task: "Implement ChatRequest schema in backend/src/modules/chat/schemas.py"
Task: "Implement placeholder word generator in backend/src/modules/chat/service.py"
```

---

## Implementation Strategy

### MVP First (and Only) Scope

This feature has exactly one user story, which is itself the MVP:

1. Complete Phase 1: Setup
2. Complete Phase 2: User Story 1
3. **STOP and VALIDATE**: Run quickstart.md end-to-end (T008, T009)

There is no incremental multi-story delivery here — the feature is complete
when Phase 2 passes its independent test.

---

## Notes

- [P] tasks = different files, no dependencies
- [US1] label maps every task to the feature's single user story for traceability
- Verify the test fails before implementing (Constitution Principle I is NON-NEGOTIABLE for this project)
- Commit after each task or logical group
- No frontend changes, no persistence, no authentication, and no real response generation are in scope for this feature (see spec.md Assumptions) — do not add them here
