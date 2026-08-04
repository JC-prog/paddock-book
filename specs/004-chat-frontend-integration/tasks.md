---

description: "Task list for Chat Frontend-Backend Integration"
---

# Tasks: Chat Frontend-Backend Integration

**Input**: Design documents from `/specs/004-chat-frontend-integration/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cors-policy.md, quickstart.md

**Tests**: Included and required — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates a failing test before implementation for every requirement in this feature.

**Organization**: This feature has a single user story (P1). All user-facing tasks carry the `[US1]` label.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 — the only story in this feature)
- Frontend paths are under `frontend/src/app/features/chat/`; the one backend path is `backend/src/main.py`

---

## Phase 1: Setup

**Purpose**: Allow the frontend's `POST /v1/chat` requests through the backend's CORS policy — a prerequisite for the real (non-mocked) integration to work at all

- [ ] T001 [P] Write a failing test verifying a CORS preflight for `POST /v1/chat` from `http://localhost:4200` succeeds, in `backend/tests/unit/test_cors.py`
- [ ] T002 Update `CORSMiddleware`'s `allow_methods` in `backend/src/main.py` to `["GET", "POST"]` per `contracts/cors-policy.md` — makes T001 pass

**Checkpoint**: The backend accepts cross-origin `POST` requests to `/v1/chat` from the frontend's dev origin.

---

## Phase 2: User Story 1 - See the backend's reply appear in the conversation (Priority: P1) 🎯 MVP

**Goal**: Sending a message calls the backend and renders its reply as a distinct, incrementally-updating bubble that completes or fails visibly, per spec.md.

**Independent Test**: Send a message with the backend running and confirm a reply bubble appears, grows incrementally, and completes; stop the backend and confirm a failure is shown instead.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (Constitution Principle I)**

- [ ] T003 [P] [US1] Write failing tests for `ChatApiService.streamReply()` against a mocked global `fetch`/`ReadableStream`: emits each word, completes cleanly on stream end (FR-004), errors on a 10-second silence via fake timers (FR-005), and errors on a mid-stream reader rejection while nothing is lost from what already arrived (FR-006) — in `frontend/src/app/features/chat/chat-api.service.spec.ts`
- [ ] T004 [P] [US1] Write failing tests for the extended `ChatService` — sending a message appends both a user message and a `streaming` assistant message, the assistant message's text grows as a mocked `ChatApiService` emits words, its status becomes `complete`/`error` accordingly, and `isSending` is `true` for the whole exchange and `false` once it settles (FR-001–FR-005, FR-007) — in `frontend/src/app/features/chat/chat.service.spec.ts`
- [ ] T005 [P] [US1] Write failing tests for `ChatInputComponent` — send (button and Enter) is disabled while `chatService.isSending()` is `true` (FR-007) — in `frontend/src/app/features/chat/chat-input.component.spec.ts`
- [ ] T006 [P] [US1] Write failing tests for `MessageBubbleComponent` — renders a `sender: 'assistant'` message with distinct styling from `'user'`, and renders a `status: 'error'` message with a visible failure indication (FR-002, FR-005, FR-006) — in `frontend/src/app/features/chat/message-bubble.component.spec.ts`

### Implementation for User Story 1

- [ ] T007 [P] [US1] Add `sender: 'user' | 'assistant'` and `status: 'complete' | 'streaming' | 'error'` to the `ChatMessage` interface in `frontend/src/app/features/chat/chat-message.model.ts` per data-model.md
- [ ] T008 [P] [US1] Implement `ChatApiService.streamReply(text): Observable<string>` — `fetch` POST, SSE line parsing per `specs/003-chat-api-sse/contracts/chat-api.md`, 10-second time-to-first-event timeout via `AbortController` (research.md) — in `frontend/src/app/features/chat/chat-api.service.ts` — makes T003 pass
- [ ] T009 [US1] Update `ChatService.sendMessage()` to append a user message and a `streaming` assistant message, subscribe to `ChatApiService.streamReply()` to grow/finalize the assistant message, and expose `isSending` — in `frontend/src/app/features/chat/chat.service.ts` (depends on T007, T008) — makes T004 pass
- [ ] T010 [US1] Update `ChatInputComponent` to bind `[disabled]` on the textarea/send button to `chatService.isSending()` and guard `onKeydown`/`submit()` against sending while `true` — in `frontend/src/app/features/chat/chat-input.component.ts` (depends on T009) — makes T005 pass
- [ ] T011 [US1] Update `MessageBubbleComponent` to style by `message.sender` (assistant bubble visually distinct from user) and `message.status` (visible indication for `'error'`) — in `frontend/src/app/features/chat/message-bubble.component.ts` (depends on T007) — makes T006 pass
- [ ] T012 [US1] Manually validate Acceptance Scenarios 1–4 via quickstart.md steps 2–4 (depends on T002, T010, T011)

**Checkpoint**: At this point, User Story 1 is fully functional and independently testable — this is the entire MVP for this feature.

---

## Phase 3: Polish & Cross-Cutting Concerns

**Purpose**: Final validation

- [ ] T013 Run full quickstart.md validation (backend `pytest`, frontend `vitest`, plus all manual scenarios from steps 2–4) and confirm SC-001–SC-004 are met (depends on T012)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **User Story 1 (Phase 2)**: The frontend test/implementation tasks (T003–T011) do not depend on Setup — they run against a mocked `fetch`, never a real CORS-gated request. Only the manual end-to-end validation (T012) depends on Setup being complete
- **Polish (Phase 3)**: Depends on User Story 1 completion

### Within User Story 1

- Tests (T003–T006) MUST be written and FAIL before their corresponding implementation tasks (Constitution Principle I)
- `ChatMessage` model (T007) and `ChatApiService` (T008) are independent of each other — transport logic never touches the message entity, by design (plan.md Structure Decision)
- `ChatService` (T009) depends on both T007 (needs the extended type) and T008 (needs the service to call)
- `ChatInputComponent` (T010) depends on `ChatService` (T009) exposing `isSending`
- `MessageBubbleComponent` (T011) depends on `ChatMessage` (T007) having `sender`/`status`

### Parallel Opportunities

- T003, T004, T005, T006 (all US1 tests) can run in parallel — four different files
- T007 and T008 (US1 implementation) can run in parallel — independent by design
- T001 (Setup) can run in parallel with any US1 test-writing task — unrelated files

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Write failing tests for ChatApiService in frontend/src/app/features/chat/chat-api.service.spec.ts"
Task: "Write failing tests for ChatService in frontend/src/app/features/chat/chat.service.spec.ts"
Task: "Write failing tests for ChatInputComponent in frontend/src/app/features/chat/chat-input.component.spec.ts"
Task: "Write failing tests for MessageBubbleComponent in frontend/src/app/features/chat/message-bubble.component.spec.ts"

# ChatMessage model and ChatApiService implementations are independent:
Task: "Extend ChatMessage interface in frontend/src/app/features/chat/chat-message.model.ts"
Task: "Implement ChatApiService in frontend/src/app/features/chat/chat-api.service.ts"
```

---

## Implementation Strategy

### MVP First (and Only) Scope

This feature has exactly one user story, which is itself the MVP:

1. Complete Phase 1: Setup
2. Complete Phase 2: User Story 1
3. **STOP and VALIDATE**: Run quickstart.md end-to-end (T012, T013)

There is no incremental multi-story delivery here — the feature is complete
when Phase 2 passes its independent test.

---

## Notes

- [P] tasks = different files, no dependencies
- [US1] label maps every task to the feature's single user story for traceability
- Verify tests fail before implementing (Constitution Principle I is NON-NEGOTIABLE for this project)
- Commit after each task or logical group, split by conventional-commit type (`feat:`, `test:`, `chore:`) rather than one combined commit
- No multi-turn conversation context, no persistence, no new authentication, and no change to the `/v1/chat` reply content are in scope for this feature (see spec.md Assumptions) — do not add them here
