---

description: "Task list for feature implementation"
---

# Tasks: Application Logging

**Input**: Design documents from `/specs/010-app-logging/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required (not optional) — Constitution Principle I (Test-First
Development) is NON-NEGOTIABLE for this project: every implementation task
below has a corresponding test task that MUST be written first, confirmed
failing, then made to pass.

**Organization**: Tasks are grouped by user story (US1, US2) per spec.md's
priorities.

## Path Conventions

Backend-only feature: `backend/src/core/`, `backend/src/modules/{auth,chat}/`,
`backend/tests/unit/`.

---

## Phase 1: Setup

**Purpose**: Project initialization

- [X] T001 No new dependency or package scaffolding is required for this
  feature — Python's stdlib `logging` module is sufficient (see
  research.md), and `backend/src/core/`, `backend/src/modules/auth/`, and
  `backend/src/modules/chat/` all already exist as packages. Nothing to
  do in this phase; recorded explicitly rather than silently skipped.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared JSON formatter and request-correlation plumbing
every other part of this feature depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T002 [P] Write failing tests for `backend/src/core/logging.py` in
  `backend/tests/unit/test_core_logging.py` — cover: `JsonFormatter`
  produces a single JSON object per line with `timestamp`, `level`,
  `logger`, `message`, and `request_id` (per `data-model.md`'s common
  envelope); any extra fields passed via a log call's `extra={...}` are
  merged into the output; `request_id` is `null` when
  `request_id_var` hasn't been set; `configure_logging()` attaches the
  formatter and a filter that injects `request_id_var`'s current value
  onto every emitted record, verified by setting the context var directly
  in the test and asserting it appears on a subsequently emitted record
- [X] T003 Implement `backend/src/core/logging.py` (`JsonFormatter`,
  `request_id_var: ContextVar[str | None]`, `configure_logging()`) to
  make T002 pass (depends on T002)

**Checkpoint**: JSON formatting and request-correlation plumbing work in
isolation — ready for the request-logging middleware and event logging.

---

## Phase 3: User Story 1 - Diagnose a reported error or slow request (Priority: P1) 🎯 MVP

**Goal**: Every backend request is logged (method/path/status/duration),
unhandled errors are logged with enough detail to diagnose without
reproducing, and all log entries from one request share a request ID.

**Independent Test**: Trigger a normal request and a request that raises
an unhandled error; confirm both produce a corresponding log entry
(per spec.md's US1 acceptance scenarios), and that a request spanning
multiple internal steps has all its entries taggable as the same request.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T004 [P] [US1] Write failing tests for the request-logging
  middleware in `backend/tests/unit/test_core_middleware.py` — cover: a
  successful request produces one `INFO` log entry with method, path,
  status code, and a duration; a request that raises an unhandled
  exception produces one `ERROR` log entry with `status_code: null` and
  exception info, and the exception still propagates so FastAPI's normal
  error handling applies (FR-002); two concurrently-handled requests each
  see only their own `request_id` (contextvar isolation, per
  research.md); a log handler raising internally (simulating a logging
  failure) does not prevent the request from completing normally (FR-007)
- [X] T005 [US1] Implement `RequestLoggingMiddleware` in
  `backend/src/core/middleware.py` to make T004 pass (depends on T003,
  T004)
- [X] T006 [US1] Wire `configure_logging()` and `RequestLoggingMiddleware`
  into `backend/src/main.py` (app startup calls `configure_logging()`
  once; middleware registered alongside the existing CORS middleware)
  (depends on T005)

**Checkpoint**: User Story 1 is fully functional and independently
testable — every request and every unhandled error is now visible in the
logs with a correlation ID, satisfying SC-001 and SC-005.

---

## Phase 4: User Story 2 - Investigate who accessed what (Priority: P2)

**Goal**: Authentication events (login success/failure, logout,
registration) and chat requests (account + department retrieved) are
recorded as explicit, credential-free log entries.

**Independent Test**: Perform a login, a failed login, a logout, and a
chat request; confirm each produces the corresponding event log entry
with the right account/department info and no password, token, or
message content (per spec.md's US2 acceptance scenarios).

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T007 [P] [US2] Write failing tests for auth event logging in
  `backend/tests/unit/test_auth_service.py` — cover: `login()` on success
  logs an `INFO` `login_succeeded` entry with `email` and `user_id`; on
  failure logs a `WARNING` `login_failed` entry with `email` and
  `user_id: null`; `logout()` looks up the token's owning account (via
  the existing `repository.get_valid_refresh_token()`) before revoking
  it and logs an `INFO` `logout_succeeded` entry with that `user_id`;
  `register()` on success logs an `INFO` `registration_succeeded` entry
  with `email` and `user_id`; none of these log records, across all four
  cases, contain the literal password string used in the test (FR-006)
- [X] T008 [US2] Modify `backend/src/modules/auth/service.py` — add the
  four log calls above to `login()`, `logout()` (plus the
  `get_valid_refresh_token()` lookup before revoking), and `register()`
  to make T007 pass (depends on T003, T007)
- [X] T009 [P] [US2] Write failing tests for chat event logging in
  `backend/tests/unit/test_chat.py` — cover: a successful chat request
  (retrieval succeeds) logs an `INFO` `chat_retrieval_succeeded` entry
  with the requesting account's `user_id` and a `departments` list
  containing the requester's department; the log record does not contain
  the request's message text nor any fragment of the streamed reply
  (FR-008); a chat request whose retrieval fails (the existing 502 path)
  does not produce this event log entry
- [X] T010 [US2] Modify `backend/src/modules/chat/router.py::post_chat` —
  add the log call above immediately after `retrieve_context()` returns
  successfully, to make T009 pass (depends on T003, T009)

**Checkpoint**: User Stories 1 AND 2 both fully functional — SC-002,
SC-003, and SC-004 are all satisfied.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation against a running backend and full-suite
regression check

- [X] T011 [P] Run the full `quickstart.md` validation against a locally
  running backend and confirm FR-001–FR-009 / SC-001–SC-005, documenting
  results in this tasks.md file — Ran the real backend against real
  Postgres. Step 1: `GET /health` produced a correct request-log entry.
  Step 2: stopped Postgres, `POST /v1/auth/login` returned a clean `500`
  (not a hang) with an `ERROR` entry showing `status_code: null` and the
  real connection-refused stack trace — SC-001 confirmed live. Step 3:
  registered a real account, confirmed `registration_succeeded` and
  `logout_succeeded` (correctly naming the same account) fired, and a
  distinctive test password never appeared anywhere in the log file (0
  occurrences, grepped) — SC-002/SC-004 confirmed live. Step 4: sent a
  chat request with a distinctive question string via the local Ollama
  embedding provider (real retrieval succeeded, empty department corpus
  → honest no-answer reply); `chat_retrieval_succeeded` fired with the
  correct account and department, and the question text never appeared
  anywhere in the log file — SC-003 confirmed live. Step 5: confirmed all
  three log lines for that chat request (including httpx's own internal
  Ollama-call log line) shared the identical `request_id` — SC-005
  confirmed live, and as a bonus showed the correlation ID design
  generalizes to third-party library logging too, not just this
  feature's own explicit calls. Did not run the optional network-drop
  spot check (quickstart Step 5's manual Wi-Fi toggle) — FR-007 is
  already covered by a real, passing unit test
  (`test_a_logging_handler_failure_does_not_fail_the_request`).
- [X] T012 Run the full backend test suite (`pytest`) and confirm no
  regressions in previously-passing tests (Constitution's CI requirement)
  — 177/177 passed (unit + integration, including live-Postgres tests
  from other features). Also re-ran the unit suite with no `.env` file
  and no env vars at all (the CI-parity check this project adopted after
  an earlier CI failure this session) — 136/136 passed with zero
  configuration, since this feature never touches `Settings()`/env vars.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately (though
  there's nothing to do; see T001)
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS both
  user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion
  only — NOT on User Story 1. Auth/chat event logging (T007–T010) uses
  `core/logging.py` directly and doesn't need `RequestLoggingMiddleware`
  to exist first (see research.md), so US1 and US2 can proceed in
  parallel once Foundational is done, even though US1 is P1.
- **Polish (Phase 5)**: Depends on both user stories being complete

### Within Each User Story

- Tests MUST be written and confirmed failing before their corresponding
  implementation task (Constitution Principle I)
- Shared plumbing (Foundational) before either story's own logging calls

### Parallel Opportunities

- T004 (US1 test) and T007/T009 (US2 tests) can run in parallel once
  Foundational (T002–T003) is complete — different files, no dependency
  on each other
- T007 and T009 (different test files) can run in parallel with each
  other within US2
- T011 and T012 (Polish) can run in parallel

---

## Parallel Example: After Foundational Completes

```bash
# US1 and US2 test-writing can start together — different files, no shared dependency:
Task: "Write failing tests for the request-logging middleware in backend/tests/unit/test_core_middleware.py"
Task: "Write failing tests for auth event logging in backend/tests/unit/test_auth_service.py"
Task: "Write failing tests for chat event logging in backend/tests/unit/test_chat.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (nothing to do)
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: every request and error is now visible in logs
   with a correlation ID — already useful for day-to-day debugging
5. This alone delivers real value even before US2's audit-trail logging
   exists

### Incremental Delivery

1. Foundational → JSON formatting + correlation plumbing proven in
   isolation
2. Add User Story 1 → operational visibility into every request/error →
   already shippable
3. Add User Story 2 → auth/chat audit trail → ship
4. Polish → full live validation + regression check

## Notes

- [P] tasks = different files, no dependencies on each other
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group, split by conventional commit
  type (test:/feat:/chore:), per this project's established convention
- Verify each test fails before implementing the code that makes it pass
