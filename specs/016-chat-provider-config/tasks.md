---

description: "Task list for feature implementation"
---

# Tasks: Chat Provider Configuration

**Input**: Design documents from `/specs/016-chat-provider-config/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/admin-api.md, quickstart.md

**Tests**: Required (not optional) — Constitution Principle I (Test-First
Development) is NON-NEGOTIABLE for this project: every implementation task
below has a corresponding test task that MUST be written first, confirmed
failing, then made to pass.

**Organization**: Tasks are grouped by user story (US1, US2, US3) per
spec.md's priorities.

## Path Conventions

`backend/requirements.txt`, `db/init/005_chat_provider_config.sql`,
`backend/src/modules/admin/{repository,service,router,schemas}.py`,
`backend/src/modules/chat/{generation,service,router}.py`,
`backend/tests/{unit,integration}/test_*.py`,
`frontend/src/app/features/admin/chat-provider/chat-provider.component.ts`,
`frontend/src/app/app.routes.ts`.

---

## Phase 1: Setup

**Purpose**: The new dependency this feature needs

- [X] T001 [P] Add `openai` to `backend/requirements.txt` and install it
  into the backend venv

  **Result**: Installed `openai==3.0.0` (pins its own `httpx2`/`httpcore2`
  packages internally — verified no conflict with the existing
  `httpx==0.28.1` pin still used by `ollama`; `pip check` reports no
  broken requirements).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The new table, its CRUD, the request/response shapes, and
the provider-dispatch scaffolding every user story builds on. Delivers a
working Ollama-only path end-to-end (identical behavior to today) so
each story only has to *add* a provider, not build the plumbing.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T002 [P] Write the new migration `db/init/005_chat_provider_config.sql`
  creating the singleton `chat_provider_settings` table exactly per
  data-model.md (columns, `CHECK`s, `id = 1` singleton pattern matching
  `003_admin_settings.sql`'s `app_settings`)

  **Result**: Applied by hand to the running local dev DB (`docker exec
  paddock-book-db-1 psql -U paddockbook -d paddockbook < db/init/005_chat_provider_config.sql`).
- [X] T003 [P] Write a failing integration test in
  `backend/tests/integration/test_admin_repository.py` (extend) for a
  new `get_chat_provider_settings(conn)` repository function — covers:
  returns `None` when no row exists yet (mirrors
  `get_log_destination_setting`'s existing None-fallback precedent);
  returns the stored row's values (as a dict) once one exists

  **Result**: Confirmed failing first (`ImportError: cannot import name
  'get_chat_provider_settings'`).
- [X] T004 Implement `get_chat_provider_settings` in
  `backend/src/modules/admin/repository.py` to make T003 pass (depends
  on T002, T003)
- [X] T005 [P] Write a failing integration test in
  `backend/tests/integration/test_admin_repository.py` (extend) for a
  new `upsert_chat_provider_settings(conn, updates: dict)` repository
  function — covers: creates the row (id=1) with the table's defaults
  plus `updates` applied, if no row exists yet; on an existing row,
  changes only the keys present in `updates`, leaving every other
  column's stored value untouched (the partial-update semantics from
  research.md/contracts/admin-api.md); always refreshes `updated_at`
- [X] T006 Implement `upsert_chat_provider_settings` in
  `backend/src/modules/admin/repository.py` to make T005 pass (depends
  on T004, T005)

  **Result**: All 4 new integration tests pass (10/10 total in the file,
  no regressions in the 6 pre-existing tests).
- [X] T007 [P] Add `ChatProviderSettingsResponse` and
  `ChatProviderSettingsUpdate` Pydantic models (both
  `ConfigDict(strict=True)`, matching this module's existing
  `LogDestinationSetting` style) to
  `backend/src/modules/admin/schemas.py` — `active_provider` typed as
  `Literal["ollama", "bedrock", "openai_compatible"] | None` on the
  Update model (per contracts/admin-api.md's request/response shapes);
  the Response model has `openai_compatible_api_key_set: bool`, never a
  raw key field (FR-011)
- [X] T008 [P] Write failing unit tests in
  `backend/tests/unit/test_admin_service.py` (extend) for
  `get_chat_provider_config(*, conn, repository=...)` — covers: returns
  this table's documented defaults (`active_provider: "ollama"`, all
  else `None`/unset) when the repository returns `None`; otherwise
  returns the stored row, translating a present
  `openai_compatible_api_key` into `openai_compatible_api_key_set: True`
  without ever including the key's value in the returned object
- [X] T009 Implement `get_chat_provider_config` in
  `backend/src/modules/admin/service.py` to make T008 pass (depends on
  T007, T008)
- [X] T010 [P] Write failing unit tests in
  `backend/tests/unit/test_admin_service.py` (extend) for
  `update_chat_provider_config(updates, *, conn, admin_user, repository=...)`
  — covers (Ollama path only at this Foundational stage — no
  Bedrock/OpenAI-compatible validation yet, that's US1/US2): setting
  `active_provider: "ollama"` always succeeds regardless of what else is
  stored (FR-006, Assumptions); calls `repository.upsert_chat_provider_settings`
  with exactly the caller's `updates` dict (no silent field-dropping);
  commits the connection on success; logs a
  `chat_provider_config_changed` event including the admin's user id but
  never the API key value (mirrors `update_log_destination`'s logging
  style, secrets excluded)
- [X] T011 Implement `update_chat_provider_config` in
  `backend/src/modules/admin/service.py` to make T010 pass — including
  the `IncompleteProviderConfigError` exception class (raised by
  US1/US2's later validation, defined now so the router task below can
  depend on it) (depends on T009, T010)
- [X] T012 [P] Write failing unit tests in
  `backend/tests/unit/test_admin_router.py` (extend) for
  `GET /v1/admin/settings/chat-provider` and
  `PUT /v1/admin/settings/chat-provider` — covers: both require
  `require_admin` (matching this router's existing dependency-injection
  test pattern); `GET` returns the service's `ChatProviderSettingsResponse`;
  `PUT` passes the request body through to
  `update_chat_provider_config` and returns its result; `PUT` maps a
  raised `IncompleteProviderConfigError` to `409 Conflict` with the
  exception's message as `detail` (mirrors `jobs/router.py`'s existing
  `DuplicateJobError` → `409` mapping)
- [X] T013 Implement both endpoints in
  `backend/src/modules/admin/router.py` to make T012 pass (depends on
  T009, T011, T012)
- [X] T014 [P] Write failing unit tests in
  `backend/tests/unit/test_chat_generation.py` (extend) replacing the
  existing `model=`/`host=`-keyword `generate_answer` calls with calls
  passing a `ChatProviderConfig(provider="ollama", ollama_model=...,
  ollama_host=...)` object instead (data-model.md's "Read shape") —
  covers the exact same behaviors the existing 5 tests in this file
  already assert (model/host used, streamed fragments yielded in order,
  context+question in the prompt, the no-relevant-info system-prompt
  instruction), now via the new signature; this is a refactor of
  existing coverage, not new behavior
- [X] T015 Implement the `ChatProviderConfig` dataclass and rewrite
  `generate_answer`'s signature to `(question, chunks, *, provider_config,
  ollama_client_factory=..., bedrock_client_factory=..., openai_client_factory=...)`
  dispatching to a private `_generate_ollama` (the prior body, unchanged
  internally) in `backend/src/modules/chat/generation.py`, to make T014
  pass — `bedrock`/`openai_compatible` branches are not implemented yet
  (US1/US2 add them); dispatching to either at this stage should raise
  a clear `NotImplementedError` rather than silently doing nothing
  (depends on T014)
- [X] T016 [P] Write a failing unit test in
  `backend/tests/unit/test_chat_service.py` (extend) for a new
  `resolve_provider_config(*, conn, admin_repository=..., settings_factory=Settings) -> ChatProviderConfig`
  function in `chat/service.py` — covers: builds a `ChatProviderConfig`
  from the admin repository's stored row, falling back to
  `settings_factory().ollama_model`/`.ollama_host`/`.aws_region` for any
  field the row leaves unset (mirrors data-model.md's "Read shape"
  column-by-column fallback table exactly)
- [X] T017 Implement `resolve_provider_config` in
  `backend/src/modules/chat/service.py` (importing
  `src.modules.admin.repository` directly, per research.md's
  cross-module precedent) to make T016 pass (depends on T004, T016)
- [X] T018 [P] Write a failing unit test in
  `backend/tests/unit/test_chat_service.py` (extend) updating
  `generate_reply`'s existing test to pass a `provider_config=` kwarg
  (a `ChatProviderConfig`) instead of relying on `settings_factory`
  alone for the model/host — covers: `generation.generate_answer` is
  called with that exact `provider_config` object; the existing
  no-chunks short-circuit behavior (yields `NO_RELEVANT_INFO_REPLY`
  without calling generation at all) is unchanged
- [X] T019 Update `generate_reply` in
  `backend/src/modules/chat/service.py` to accept and forward
  `provider_config` to `generation.generate_answer` to make T018 pass
  (depends on T015, T018)
- [X] T020 Wire `chat/router.py::post_chat()` to open a second short-lived
  connection after `retrieve_context()`'s connection has closed, call
  `resolve_provider_config(conn=...)`, close that connection, then pass
  the result into `generate_reply(..., provider_config=...)` — matches
  this module's existing one-connection-per-purpose style; no DB
  connection is held open for the duration of the SSE stream itself
  (depends on T017, T019)

**Checkpoint**: A fresh install behaves exactly as before this feature
(Ollama, unconfigurable) — `GET`/`PUT /v1/admin/settings/chat-provider`
exist and work for the Ollama case, but Bedrock/OpenAI-compatible aren't
usable yet. No user story is demonstrable end-to-end until at least one
of US1/US2 lands.

---

## Phase 3: User Story 1 - Switch the active chat provider (Priority: P1)

**Goal**: An admin can select AWS Bedrock, enter a model identifier, save,
and have the next chat request answered via that Bedrock model — plus
the general "switch provider, takes effect immediately, survives a
restart" capability this story is really about.

**Independent Test**: Configure a Bedrock model via `PUT`, confirm `GET`
reflects it as active, send a chat message, confirm the answer streams
from Bedrock's Converse API rather than Ollama.

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T021 [P] [US1] Write failing unit tests in
  `backend/tests/unit/test_admin_service.py` (extend) for
  `update_chat_provider_config`'s Bedrock validation (FR-013) — covers:
  setting `active_provider: "bedrock"` without a `bedrock_model` already
  present (in this update or previously stored) raises
  `IncompleteProviderConfigError` and does **not** call
  `repository.upsert_chat_provider_settings` at all (nothing partially
  saved); setting `active_provider: "bedrock"` together with
  `bedrock_model` in the same update succeeds; setting
  `active_provider: "bedrock"` succeeds when `bedrock_model` was already
  saved in a prior call (the merged-row check from data-model.md, not
  just this request's body)
- [X] T022 [US1] Add the Bedrock branch to
  `update_chat_provider_config` in
  `backend/src/modules/admin/service.py` to make T021 pass (depends on
  T011, T021)
- [X] T023 [P] [US1] Write failing unit tests in
  `backend/tests/unit/test_chat_generation.py` (extend) for
  `_generate_bedrock` — with a mocked Bedrock client (injected via
  `bedrock_client_factory`, matching this file's existing
  `client_factory` DI pattern) — covers: calls `converse_stream` with
  the configured `bedrock_model` and the built messages translated into
  the Converse API's message format; yields decoded text fragments in
  order as they arrive from the (mocked) stream; the blocking iteration
  happens off the event loop (assert the work is dispatched via
  `asyncio.to_thread` or equivalent — mock/patch that call and assert
  it's used, per research.md's threading-bridge decision)
- [X] T024 [US1] Implement `_generate_bedrock` in
  `backend/src/modules/chat/generation.py` — `boto3` Bedrock Runtime
  client via `bedrock_client_factory` (defaulting to a real
  `boto3.client("bedrock-runtime", region_name=provider_config.aws_region)`,
  matching `core/embeddings.py::get_bedrock_client`'s existing
  construction), the `asyncio.to_thread` + `asyncio.Queue` bridge from
  research.md, wired into `generate_answer`'s dispatch — to make T023
  pass (depends on T015, T023)
- [X] T025 [P] [US1] Write a failing unit test in
  `backend/tests/unit/test_admin_router.py` (extend) confirming `PUT`
  returns `409 Conflict` with a Bedrock-specific message when
  `IncompleteProviderConfigError` is raised for a missing
  `bedrock_model` (extends T012's generic 409-mapping test with the
  concrete Bedrock case from contracts/admin-api.md)
- [X] T026 [US1] Verify T013's existing exception handling already
  satisfies T025 without changes (the mapping is generic per T011); if
  it doesn't, adjust `backend/src/modules/admin/router.py` (depends on
  T022, T025)
- [X] T027 [P] [US1] Write a failing test in
  `frontend/src/app/features/admin/chat-provider/chat-provider.component.spec.ts`
  (NEW) — mirrors `admin.component.spec.ts`'s inline-`HttpClient`,
  signals-based testing style — covers: on load, `GET`s the current
  config and clearly displays the active provider (satisfies User
  Story 1 Acceptance Scenario 1 and lays the groundwork for US3);
  selecting "AWS Bedrock" reveals a model-identifier text input; saving
  with a model identifier `PUT`s `{active_provider: "bedrock",
  bedrock_model: "..."}` and, on success, updates the displayed active
  provider; saving without a model identifier for Bedrock shows a clear
  inline error rather than silently failing or showing a raw HTTP body
  (translates the `409` from contracts/admin-api.md into a readable
  message)
- [X] T028 [US1] Implement
  `frontend/src/app/features/admin/chat-provider/chat-provider.component.ts`
  (provider dropdown: Ollama/Bedrock/OpenAI-compatible; Bedrock model
  field; save button; active-provider display; inline error rendering)
  to make T027 pass, and register the `/admin/chat-provider` route in
  `frontend/src/app/app.routes.ts` with the existing
  `[authGuard, adminGuard]` pair (matching `/admin` and `/admin/jobs`'s
  existing route entries) (depends on T013, T027)

**Checkpoint**: User Story 1 is fully functional and independently
testable — an admin can switch to Bedrock (or back to Ollama) and chat
answers come from the newly active provider on the very next request.
SC-001, SC-002, SC-006 (Bedrock half) hold.

---

## Phase 4: User Story 2 - Configure the OpenAI-compatible provider (Priority: P1)

**Goal**: An admin can enter a base URL, API key, and model name for the
OpenAI-compatible provider, save, activate it, and have chat answers
come from that endpoint — with the key never displayed back afterward.

**Independent Test**: `PUT` a base URL/key/model, confirm `GET` shows the
base URL and model plus `openai_compatible_api_key_set: true` but no key
value, send a chat message, confirm the answer streams from that
endpoint.

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T029 [P] [US2] Write failing unit tests in
  `backend/tests/unit/test_admin_service.py` (extend) for
  `update_chat_provider_config`'s OpenAI-compatible validation (FR-012)
  — covers: setting `active_provider: "openai_compatible"` without all
  three of base URL/key/model already present (this update or
  previously stored, merged) raises `IncompleteProviderConfigError` and
  saves nothing; succeeds once all three are present, whether supplied
  in this call or a prior one (the FR-015 retention case: a second call
  sending only `{"active_provider": "openai_compatible"}` after a prior
  call already saved the credential)
- [X] T030 [US2] Add the OpenAI-compatible branch to
  `update_chat_provider_config` in
  `backend/src/modules/admin/service.py` to make T029 pass (depends on
  T022, T029)
- [X] T031 [P] [US2] Write failing unit tests in
  `backend/tests/unit/test_chat_generation.py` (extend) for
  `_generate_openai_compatible` — with a mocked `openai.AsyncOpenAI`
  client injected via `openai_client_factory` — covers: the client is
  constructed with the configured `base_url` and `api_key`; calls
  `chat.completions.create` with the configured `model`, the built
  messages, and `stream=True`; yields decoded text-delta fragments in
  order as they arrive from the (mocked) async stream
- [X] T032 [US2] Implement `_generate_openai_compatible` in
  `backend/src/modules/chat/generation.py` using `openai.AsyncOpenAI`,
  wired into `generate_answer`'s dispatch, to make T031 pass (depends
  on T024, T031)
- [X] T033 [P] [US2] Write a failing test in
  `frontend/src/app/features/admin/chat-provider/chat-provider.component.spec.ts`
  (extend) — covers: selecting "OpenAI-compatible" reveals base
  URL/API key/model inputs; saving with all three `PUT`s them together
  with `active_provider: "openai_compatible"`; after a successful save,
  reloading the page (fresh `GET`) shows the saved base URL and model
  plus a "key saved" indicator, with no key value ever appearing
  anywhere in the rendered page or in the mocked HTTP response the test
  asserts against (FR-011); saving with any of the three fields empty
  shows a clear inline error
- [X] T034 [US2] Extend
  `frontend/src/app/features/admin/chat-provider/chat-provider.component.ts`
  with the OpenAI-compatible fields and masked-credential display to
  make T033 pass (depends on T028, T033)

**Checkpoint**: User Stories 1 AND 2 both work independently — an admin
can configure and activate any of the three providers, and switching
between them (including back to a previously configured one) works
without re-entering credentials. SC-001 through SC-006 all hold.

---

## Phase 5: User Story 3 - View current provider status (Priority: P2)

**Goal**: An admin opening the configuration page with no changes
pending immediately sees which provider is active — already true by
construction once US1 lands (the page always shows current state on
load), so this story is validated rather than newly built.

**Independent Test**: Open the page with no pending changes; confirm the
active provider is clearly indicated.

- [X] T035 [P] [US3] Write a dedicated test in
  `frontend/src/app/features/admin/chat-provider/chat-provider.component.spec.ts`
  (extend) isolating User Story 1's Acceptance Scenario 1 as its own
  named case: given a `GET` response with a specific `active_provider`
  and no user interaction at all, the page's displayed active-provider
  indicator matches it exactly on initial load — confirms this holds as
  its own regression-checkable behavior, independent of any save flow
- [X] T036 [US3] If T035 fails, adjust
  `frontend/src/app/features/admin/chat-provider/chat-provider.component.ts`'s
  initial-load rendering; if T035 already passes from US1's
  implementation (expected — see Goal above), no code change is needed,
  only the new test itself (depends on T028, T035)

**Checkpoint**: All three user stories are independently functional and
tested — the feature is complete end-to-end.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation against a real backend, plus full-suite
regression check

- [X] T037 [P] Run the full `quickstart.md` validation, confirming
  FR-001–FR-015 / SC-001–SC-006, documenting results in this tasks.md
  file. Steps 1–5 and 8 require only local Ollama + Postgres; steps 6–7
  (live OpenAI-compatible / Bedrock calls) are optional per
  quickstart.md and may instead be confirmed via T023/T031's mocked
  unit coverage if live credentials aren't available in this
  environment

  **Results (live-validated against a real running backend on
  `:8010`, real Postgres, real local Ollama with `llama3.2`):**
  - **Step 1 (fresh defaults, FR-001)**: `GET` on a database with no
    prior row returned `{"active_provider": "ollama", ...,
    "openai_compatible_api_key_set": false}` — matches the documented
    fresh-install default exactly.
  - **Step 2 (existing chat behavior unchanged, regression check)**: A
    real `POST /v1/chat` request through the new dispatch (Ollama
    branch) streamed successfully end-to-end; response was the
    deterministic `NO_RELEVANT_INFO_REPLY` short-circuit (expected — the
    fresh test account's department had no ingested content), confirming
    `resolve_provider_config` → `generate_reply` → `generation.generate_answer`
    all wired correctly with no errors.
  - **Step 3 (activation blocking, FR-012/FR-013)**: `PUT
    {"active_provider": "bedrock"}` and `PUT {"active_provider":
    "openai_compatible"}` (both with no prior settings) each returned
    `409`, exactly as designed — confirmed without needing any real
    Bedrock/OpenAI-compatible access, matching research.md's "pure
    database-state validation" design.
  - **Step 4 (OpenAI-compatible credential entry, FR-004/FR-011)**: `PUT`
    with a base URL/key/model returned `200` with
    `"openai_compatible_api_key_set": true` and the base URL/model
    echoed back — the actual key value never appeared anywhere in the
    response.
  - **Step 5 (retention across a switch away and back, FR-015)**:
    Switched to `ollama`, then back to `openai_compatible` sending only
    `{"active_provider": "openai_compatible"}` (no credential fields) —
    returned `200`, not `409`, confirming the previously saved credential
    was retained and the partial-update `PUT` semantics work as
    documented.
  - **Steps 6–7 (live OpenAI-compatible / Bedrock chat generation)**: Not
    run live — no real OpenAI-compatible endpoint or AWS Bedrock access
    available in this environment, exactly the case quickstart.md
    anticipates. Covered instead by T023's and T031's mocked unit tests
    (10 tests total across both provider branches, including the
    `asyncio.to_thread` bridging assertion for Bedrock).
  - **Step 8 (frontend page)**: No browser automation tool was available
    this session, so full interactive walkthrough wasn't performed live.
    Partially verified instead: the Angular dev server built and served
    `/admin/chat-provider` successfully (`200`, with
    `chat-provider-component` as its own 13.08 kB lazy chunk — confirming
    no build/runtime resolution errors), and the full interactive
    behavior described in this step (load-and-display, provider
    selection revealing the right fields, save/error handling, key never
    shown) is covered by the 11 passing tests in
    `chat-provider.component.spec.ts` (T027/T033/T035).
  - Test artifacts (temporary admin account, `chat_provider_settings` row)
    reset/cleaned up after validation.
- [X] T038 Run the full backend test suite (`pytest`), confirm no
  regressions, and re-confirm this project's established CI-parity
  discipline: the backend unit suite still passes with no `.env`/env
  vars at all — including a fresh check that importing
  `chat/generation.py` (the first module in this project to import
  `openai`) introduces no new import-time issue

  **Results:**
  - Full suite: `373 passed` (no regressions). One leftover committed
    row in `chat_provider_settings` from T037's live curl testing broke
    `test_get_chat_provider_settings_returns_none_when_no_row_exists`
    on the first run (a real cleanup gap, not a code defect — the
    integration test fixture's `rollback()` only undoes work done
    inside the test itself, not separately-committed rows from manual
    live testing); deleted the row and re-ran clean.
  - No-`.env` CI-parity check (`.env` moved aside, `env -i` with only
    `PATH`/`HOME`): `import src.modules.chat.generation` succeeds —
    `openai` introduces no import-time dependency on settings/env vars —
    and the full unit suite (`tests/unit`) still passes: `301 passed`.
    `.env` restored afterward.
- [X] T039 Run the full frontend test suite (`vitest run`), confirm no
  regressions

  **Result**: `19 test files, 100 tests passed` — no regressions.
- [X] T040 Bump `VERSION`/`frontend/package.json`/`backend/src/__init__.py`
  (to 0.15.0) and add a linked `CHANGELOG.md` entry, per the
  constitution's Development Workflow rule

  **Results**: All three bumped `0.14.0` → `0.15.0`; `CHANGELOG.md`
  entry added under `[0.15.0] - 2026-08-13`, linked to
  `specs/016-chat-provider-config/spec.md`, including an explicit "Known
  limitation" note on the plain-text API key storage tradeoff.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001's `openai` install,
  needed before T031/T032 in US2, though not blocking the rest of
  Foundational) — BLOCKS all three user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion;
  independently testable from US1 at the backend level (T029–T032 don't
  need Bedrock's branch), but shares the same frontend component file
  as US1 (T034 extends T028's file) — build US1's frontend task first
  to avoid the same-file conflict
- **User Story 3 (Phase 5)**: Depends on US1 (T028) — its check is
  against behavior US1 already delivers
- **Polish (Phase 6)**: Depends on all three user stories being complete

### Within Each User Story

- Tests MUST be written and confirmed failing before their corresponding
  implementation task (Constitution Principle I)
- Backend validation (service layer) before the frontend task that
  surfaces its error message, within each story
- Frontend tasks within US1/US2/US3 touch the same component file
  sequentially (T028 → T034 → T036), not in parallel with each other

---

## Parallel Example: Foundational Phase

```bash
# Independent files, writable together:
Task: "Write migration db/init/005_chat_provider_config.sql"
Task: "Write failing integration tests for get_chat_provider_settings in backend/tests/integration/test_admin_repository.py"
Task: "Add ChatProviderSettingsResponse/Update schemas to backend/src/modules/admin/schemas.py"
Task: "Write failing unit tests for generate_answer's new ChatProviderConfig signature in backend/tests/unit/test_chat_generation.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (Bedrock)
4. **STOP and VALIDATE**: Configure Bedrock via the admin page, confirm a
   real chat request answers via Bedrock
5. Deploy/demo if ready — Ollama (Foundational) + Bedrock (US1) already
   cover the two providers most likely to matter first (local dev,
   AWS production)

### Incremental Delivery

1. Complete Setup + Foundational → Ollama-only behavior, unchanged from
   today, now flowing through the new dispatch
2. Add User Story 1 → Bedrock switchable → validate
3. Add User Story 2 → OpenAI-compatible switchable → validate
4. Add User Story 3 → status-display behavior explicitly regression-tested
5. Each story adds value without breaking the previous one

---

## Notes

- [P] tasks = different files, or independent additions to the same file
  with no ordering dependency between them
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing
- Commit after each task or logical group, split by conventional type
  (feat/test/chore), per this session's established pattern
- Stop at any checkpoint to validate a story independently
