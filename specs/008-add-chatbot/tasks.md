---

description: "Task list for Retrieval-Grounded Chat Answers"
---

# Tasks: Retrieval-Grounded Chat Answers

**Input**: Design documents from `/specs/008-add-chatbot/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/chat-api.md, quickstart.md

**Tests**: Constitution Principle I (Test-First, NON-NEGOTIABLE) applies. `generation` and `service` are true unit tests with no live dependency (Ollama is mocked); `retrieval` needs a real Postgres+pgvector and lives in `backend/tests/integration/`, per the Principle II distinction established since feature 005. `core/embeddings.py` (promoted from feature 006) gets its own dedicated unit test rather than only being covered indirectly through `modules/ingestion/embeddings.py`'s existing test. Vitest for `chat-api.service.ts`'s auth-header attachment.

**Organization**: Tasks are grouped by user story from spec.md (US1 = P1 grounded answer, US2 = P2 honest "no relevant information"). `retrieval.py`'s basic query capability is Foundational since both stories depend on it identically — what differs between the stories is what `service.py`/`generation.py` do with an empty result, which is genuinely new logic added in US2, not just re-testing US1's mechanism.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Paths are `backend/`- or `frontend/`-relative except where stated in full

---

## Phase 1: Setup

**Purpose**: Add the new backend dependency

- [X] T001 [P] Add `ollama==0.6.2` to `backend/requirements.txt` (research.md)

**Checkpoint**: Dependency installable.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config, the promoted shared embedding call, and basic department-filtered retrieval are used identically by both user stories. None of this is story-specific.

**⚠️ CRITICAL**: No user story implementation task may start until this phase is complete.

- [X] T002 [P] Write failing unit tests in `backend/tests/unit/test_config.py` for `Settings.ollama_model` (defaults to `"llama3.2"`) and `Settings.ollama_host` (defaults to `"http://localhost:11434"`) — confirmed failing before `config.py` is updated (Constitution Principle I)
- [X] T003 Extend `backend/src/core/config.py`'s `Settings` with `ollama_model`, `ollama_host` — makes T002 pass (depends on T002)
- [X] T004 [P] Write failing unit tests in `backend/tests/unit/test_core_embeddings.py` (new) — `get_bedrock_client` returns a client scoped to the given region; `embed_text` calls Titan V2's `InvokeModel` with the expected model ID and dimensions and returns the embedding vector; propagates a clear error on call failure — this is the same coverage feature 006's `test_ingestion_embeddings.py` already has for `embed_chunk`, now at its true source
- [X] T005 Implement `backend/src/core/embeddings.py` — `get_bedrock_client`, `embed_text` (promoted from `modules/ingestion/embeddings.py`, research.md) — makes T004 pass (depends on T004)
- [X] T006 Update `backend/src/modules/ingestion/embeddings.py` — `embed_chunk` now delegates to `core.embeddings.embed_text`/`get_bedrock_client`; update `backend/tests/unit/test_ingestion_embeddings.py`'s imports (`EMBEDDING_MODEL_ID`/`EMBEDDING_DIMENSIONS` now come from `core.embeddings`) and confirm every existing assertion still passes unchanged — proves the refactor didn't change `embed_chunk`'s observable behavior (depends on T005)
- [X] T007 [P] Write a failing integration test in `backend/tests/integration/test_chat_retrieval.py` (new) — requires the local database running; a department-filtered, cosine-distance-ordered query returns only chunks matching the given department; returns an empty list for a department with no ingested chunks — confirmed failing (module doesn't exist) before implementation
- [X] T008 Implement `backend/src/modules/chat/retrieval.py` — `embed_question` (wraps `core.embeddings.embed_text`) and `retrieve_relevant_chunks` (`WHERE department = %s ORDER BY embedding <=> %s::vector LIMIT 5`, research.md) — makes T007 pass (depends on T005, T007)

**Checkpoint**: Config, the shared embedding call, and basic retrieval all exist and are tested — every user story can now be built on top of them, and feature 006's ingestion behavior is unaffected.

---

## Phase 3: User Story 1 - Get a grounded answer to a regulation question (Priority: P1) 🎯 MVP

**Goal**: A logged-in staff member asking about content ingested for their department receives an answer grounded in that content, per FR-001–FR-004, FR-006, FR-007 (spec.md).

**Independent Test**: With a regulation document already ingested for a staff member's department, ask a question whose answer clearly exists in that content, and confirm the response reflects that content rather than the old fixed placeholder string (spec.md's own Independent Test for this story).

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (Constitution Principle I)**

- [X] T009 [P] [US1] Write failing unit tests in `backend/tests/unit/test_chat_generation.py` (new) — `generate_answer` constructs a prompt including the retrieved chunk text and the question, calls a mocked Ollama async client with `stream=True`, and yields the response fragments in order
- [X] T010 [P] [US1] Write failing unit tests in `backend/tests/unit/test_chat_service.py` (new) — with retrieval and generation mocked, the service embeds the question, retrieves chunks filtered to the requester's department, and passes them to generation, yielding its streamed output
- [X] T011 [P] [US1] Write failing/updated unit tests in `backend/tests/unit/test_chat.py` — `POST /v1/chat` returns `401` without a valid access token (feature 007's `get_current_user`); an authenticated request (service mocked) streams the service's generated fragments, not the old fixed placeholder
- [X] T012 [P] [US1] Write failing Vitest test additions in `frontend/src/app/features/chat/chat-api.service.spec.ts` — the outgoing request includes an `Authorization: Bearer <token>` header sourced from `AuthService.getAccessToken()` (feature 007)

### Implementation for User Story 1

- [X] T013 [US1] Implement `generate_answer` in `backend/src/modules/chat/generation.py` — makes T009 pass (depends on T009)
- [X] T014 [US1] Implement orchestration in `backend/src/modules/chat/service.py` — replaces `generate_placeholder_reply`; embeds the question, retrieves chunks, calls generation — makes T010 pass (depends on T008, T013, T010)
- [X] T015 [US1] Update `backend/src/modules/chat/router.py` — `POST /v1/chat` gains `Depends(get_current_user)` and calls the new service, per contracts/chat-api.md — makes T011 pass (depends on T014, T011). **Real pre-existing bug found and fixed**: `get_current_user` (feature 007) used `settings: Settings = Depends(Settings)`, which crashes FastAPI's body-model generation as soon as a route combines it with a Pydantic request body — this is the first route to do so. Fixed by having `get_current_user` call `Settings()` directly, matching every other endpoint in the codebase; updated `test_security.py`'s 4 affected tests and added an autouse env-var fixture there so `Settings()` resolves predictably in tests regardless of a developer's local `backend/.env`. Also restructured `service.py`/`router.py`: retrieval now runs eagerly *before* the SSE stream opens (a new `retrieve_context` function), so a Bedrock/DB failure returns a clean `502` instead of breaking an already-opened stream — found by actually running a live authenticated request and observing the raw connection drop, not by inspection. `contracts/chat-api.md` updated to match and to pin the exact status code.
- [X] T016 [US1] Update `frontend/src/app/features/chat/chat-api.service.ts` — attach the `Authorization` header — makes T012 pass (depends on T012)
- [X] T017 [US1] Manually validate Acceptance Scenarios 1–3 via quickstart.md steps 1–4, 6, and 8's login/happy-path portion (depends on T015, T016) — **partial**: validated live — unauthenticated rejection (401), and (after finding/fixing the retrieval-eagerness bug above) the retrieval-failure path returning a clean 502. Could not validate the actual grounded-answer/department-scoping happy path live — no AWS credentials in this environment (same gap as feature 006), and it blocks the *entire* chat flow here since generating the question's embedding also requires Bedrock, not just ingestion. Covered instead by the full mocked/integration suite (120/120 backend passing) — `test_chat_retrieval.py` proves department-filtering and ordering against a real Postgres+pgvector with controlled embedding vectors; `test_chat_service.py`/`test_chat_generation.py` prove the orchestration and prompt construction with Ollama mocked.

**Checkpoint**: Grounded answers work end-to-end against real ingested content — this is the MVP.

---

## Phase 4: User Story 2 - Get an honest answer when nothing relevant exists (Priority: P2)

**Goal**: The assistant clearly states it doesn't have relevant information rather than fabricating an answer, per FR-005 (deterministic empty-corpus case) and FR-008 (best-effort retrieved-but-irrelevant case) (spec.md).

**Independent Test**: Ask a question with no relevant match in the ingested content (e.g. an empty knowledge base, or an unrelated topic) and confirm the assistant clearly states it doesn't have an answer, without inventing one (spec.md's own Independent Test for this story).

### Tests for User Story 2 ⚠️

- [ ] T018 [P] [US2] Write failing unit test additions in `backend/tests/unit/test_chat_service.py` — when retrieval returns zero chunks, the service returns the fixed "no relevant information" response and generation is never called (FR-005's deterministic short-circuit, research.md)
- [ ] T019 [P] [US2] Write failing unit test additions in `backend/tests/unit/test_chat_generation.py` — the constructed prompt includes an explicit instruction telling the model to say it doesn't have relevant information when the provided context doesn't answer the question (FR-008)

### Implementation for User Story 2

- [ ] T020 [US2] Update `backend/src/modules/chat/service.py` — add the empty-retrieval short-circuit — makes T018 pass (depends on T014, T018)
- [ ] T021 [US2] Update `backend/src/modules/chat/generation.py` — add the honesty instruction to the system prompt — makes T019 pass (depends on T013, T019)
- [ ] T022 [US2] Manually validate Acceptance Scenarios 1–2 via quickstart.md step 5 (empty corpus and an unrelated question) (depends on T020, T021)

**Checkpoint**: Both user stories are functional — this is the complete feature.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation

- [ ] T023 Run the full quickstart.md validation (all steps) plus the full automated suite (`backend` unit + integration, `frontend` unit) and confirm SC-001–SC-006 are met, including the SC-002/SC-003 distinction from the post-planning clarification (depends on T017, T022)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS both user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion, and on User Story 1's `service.py`/`generation.py` already existing (T014/T013) since it adds to those same files rather than creating them
- **Polish (Phase 5)**: Depends on both user stories being complete

### Within Each User Story

- Tests MUST be written and FAIL before their corresponding implementation (Constitution Principle I)
- `generation.py` and `service.py` before `router.py`; `router.py` before manual validation
- Frontend `chat-api.service.ts` change is independent of the backend implementation tasks — different files, only their respective tests gate them

### Parallel Opportunities

- T002 and T004 (Foundational tests) can run in parallel — independent files; T007 (integration test) can be written alongside them
- T009, T010, T011, T012 (US1 tests) can run in parallel — four independent files
- T018 and T019 (US2 tests) can run in parallel — two independent files, each extending a different existing test file

---

## Parallel Example: User Story 1

```bash
# Once Foundational is done, these four tests can proceed together:
Task: "Write backend/tests/unit/test_chat_generation.py"
Task: "Write backend/tests/unit/test_chat_service.py"
Task: "Update backend/tests/unit/test_chat.py"
Task: "Write frontend/src/app/features/chat/chat-api.service.spec.ts additions"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks both stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test grounded answers independently against real ingested content (T017)
5. Deploy/demo if ready — a staff member gets real answers, though nothing yet guarantees honesty when content doesn't exist

### Incremental Delivery

1. Complete Setup + Foundational → shared infrastructure ready
2. Add User Story 1 (grounded answers) → test independently → deploy/demo (MVP!)
3. Add User Story 2 (honest "no relevant information") → test independently → deploy/demo
4. Complete Polish → full quickstart.md validation

---

## Notes

- [P] tasks = different files, no dependencies
- [US1]/[US2] labels map every Phase 3–4 task to its spec.md story for traceability
- Verify each test fails before implementing (Constitution Principle I is NON-NEGOTIABLE for this project)
- Commit after each task or logical group, split by conventional-commit type (`feat:`, `test:`, `chore:`) rather than one combined commit
- Guardrails against prompt injection/adversarial manipulation are explicitly out of scope (spec.md Assumptions) — do not add them here
- No uncalibrated distance-threshold cutoff in retrieval (research.md) — do not add one here
- The Bedrock production LLM swap is a documented future decision, not part of this feature — do not build a Bedrock generation path here
