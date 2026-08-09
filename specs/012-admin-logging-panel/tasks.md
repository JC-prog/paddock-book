---

description: "Task list for feature implementation"
---

# Tasks: Admin Logging Panel

**Input**: Design documents from `/specs/012-admin-logging-panel/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required (not optional) — Constitution Principle I (Test-First
Development) is NON-NEGOTIABLE for this project: every implementation task
below has a corresponding test task that MUST be written first, confirmed
failing, then made to pass.

**Organization**: Tasks are grouped by user story (US1, US2) per spec.md's
priorities.

## Path Conventions

Web application: `db/init/`, `backend/src/{core,modules/{auth,admin}}/`,
`backend/tests/{unit,integration}/`, `frontend/src/app/{core/auth,features/admin}/`.

---

## Phase 1: Setup

**Purpose**: Schema and module scaffolding this feature needs

> **NOTE: Write T001 FIRST, confirm it FAILS, then write the migration.**

- [X] T001 [P] Write a failing integration test for the migration in
  `backend/tests/integration/test_admin_migration.py` — cover: after
  applying `db/init/003_admin_settings.sql` against a real Postgres
  instance, `users` has an `is_admin` column that defaults to `false`,
  and `app_settings` exists as an empty table (no `SELECT` yet returns
  the built-in `CHECK (id = 1)` violation until a row is actually
  inserted)
- [X] T002 Add `db/init/003_admin_settings.sql` (`users.is_admin boolean
  not null default false`; `app_settings (id smallint primary key
  default 1 check (id = 1), log_to_file boolean not null default
  true)`) to make T001 pass (depends on T001)
- [X] T003 [P] Create `backend/src/modules/admin/__init__.py` (empty
  module init, matching every other module's pattern)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `is_admin` needs to exist end-to-end (DB → JWT claim →
`get_current_user` → a shared authorization dependency, and threaded
through login/register/refresh) before either user story can be
meaningfully tested — US1's access control and US2's promotion both
depend on it being real, not just a database column.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T004 [P] Write failing tests for `is_admin` in JWT claims and a new
  `require_admin` dependency in `backend/tests/unit/test_security.py`
  (extend) — cover: `create_access_token` includes `is_admin` in the
  payload; `decode_access_token` returns it; `get_current_user`'s
  returned claims include it; `require_admin` returns the claims
  unchanged for `is_admin: true` and raises `403` for `is_admin: false`
- [X] T005 Implement `is_admin` in `backend/src/core/security.py`
  (`create_access_token`/`decode_access_token` signature changes,
  `require_admin` dependency next to `get_current_user`) to make T004
  pass (depends on T004)
- [X] T006 [P] Write failing tests for `is_admin` flowing through
  login/register/refresh in `backend/tests/unit/test_auth_service.py`
  (extend) — cover: each of `login()`, `register()`,
  `refresh_access_token()` returns `is_admin` in its result dict,
  sourced from the account row, and passes it to
  `security.create_access_token`
- [X] T007 Modify `backend/src/modules/auth/repository.py` (`is_admin` in
  every user `SELECT`/`RETURNING`), `backend/src/modules/auth/service.py`
  (`_issue_session` threads it through to `create_access_token`), and
  `backend/src/modules/auth/schemas.py` (`is_admin: bool` on
  `UserPublic`) to make T006 pass (depends on T005, T006)

**Checkpoint**: `is_admin` is real end-to-end — a promoted account's next
login/refresh reflects it, and `require_admin` correctly gates on it.
Ready for both user stories.

---

## Phase 3: User Story 1 - Change where logs are persisted, without touching a terminal (Priority: P1) 🎯 MVP

**Goal**: An admin can view and change the log-destination setting
through a panel; the change is durable, takes effect on the next
restart, is rejected for non-admins, and is recorded as an audit event.

**Independent Test**: As an admin, view and change the setting through
the API/panel, restart the backend, confirm the new setting is in
effect; as a non-admin, confirm the same addresses are rejected (per
spec.md's US1 acceptance scenarios).

### Backend: setting storage and API

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T008 [P] [US1] Write failing tests for the log-destination
  repository functions in `backend/tests/integration/test_admin_repository.py`
  (real Postgres) — cover: `get_log_destination_setting()` returns
  `None` when no row exists yet; `set_log_destination_setting()` creates
  the row on first call and updates it (upsert) on subsequent calls;
  `get_log_destination_setting()` reflects the current value afterward
- [X] T009 [US1] Implement `get_log_destination_setting()` /
  `set_log_destination_setting()` in
  `backend/src/modules/admin/repository.py` to make T008 pass (depends
  on T002, T008)
- [X] T010 [P] [US1] Write failing tests for the service layer in
  `backend/tests/unit/test_admin_service.py` — cover:
  `get_log_destination()` falls back to `Settings.log_to_file`'s
  `.env`-based default when the repository returns `None`;
  `update_log_destination()` calls the repository's setter and logs a
  `log_destination_changed` event with `admin_user_id`/`new_value` (per
  data-model.md)
- [X] T011 [US1] Implement `get_log_destination()` /
  `update_log_destination()` in `backend/src/modules/admin/service.py`
  to make T010 pass (depends on T009, T010)
- [X] T012 [P] [US1] Write failing tests for the router in
  `backend/tests/unit/test_admin_router.py` — cover: `GET`/`PUT
  /v1/admin/settings/log-destination` return `401` unauthenticated and
  `403` for a non-admin; `GET` returns the current setting; `PUT` updates
  it and returns the new value; `PUT` with a missing/non-boolean body
  returns `422` (per `contracts/admin-api.md`)
- [X] T013 [US1] Implement `backend/src/modules/admin/router.py` (`GET`/
  `PUT /v1/admin/settings/log-destination`, gated by `require_admin`) and
  register it in `backend/src/main.py` to make T012 pass (depends on
  T005, T011, T012)

### Backend: `configure_logging()` reads the DB-backed value

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T014 [P] [US1] Write failing tests for `configure_logging()`'s new
  `db_log_to_file_factory` parameter in
  `backend/tests/unit/test_core_logging.py` (extend) — cover: when the
  factory is provided and returns a value, it overrides
  `Settings.log_to_file`; when the factory raises or returns `None`
  (no row yet), it falls back silently to `Settings.log_to_file` (no
  warning — this is the expected fallback path, distinct from the
  existing warned failure modes); when the factory argument is omitted
  entirely (`None` default), behavior is unchanged from before this
  feature (regression check against features 010/011)
- [X] T015 [US1] Implement the `db_log_to_file_factory` parameter in
  `backend/src/core/logging.py::configure_logging()` to make T014 pass
  (depends on T014)
- [X] T016 [US1] Wire the real DB-backed factory into
  `backend/src/main.py` — a small function that opens its own
  short-lived `psycopg` connection, queries `app_settings`, and closes
  it, wrapped by T015's existing try/except (no live Postgres needed for
  this to succeed at import time — matches research.md's CI-parity
  reasoning) (depends on T009, T015)

### Frontend

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T017 [P] [US1] Write failing tests for `is_admin` on the session in
  `frontend/src/app/core/auth/auth.service.spec.ts` (extend) — cover:
  the `AuthUser` interface includes `is_admin`; login/refresh/register
  responses populate it on `currentUser()`
- [X] T018 [US1] Add `is_admin: boolean` to the `AuthUser` interface in
  `frontend/src/app/core/auth/auth.service.ts` to make T017 pass
  (depends on T017)
- [X] T019 [P] [US1] Write failing tests for a new `adminGuard` in
  `frontend/src/app/core/auth/admin.guard.spec.ts` — cover: allows
  navigation when `currentUser()?.is_admin` is `true`; redirects
  otherwise (mirroring `authGuard`'s existing pattern)
- [X] T020 [US1] Implement `frontend/src/app/core/auth/admin.guard.ts` to
  make T019 pass (depends on T018, T019)
- [X] T021 [P] [US1] Write failing tests for the admin panel component in
  `frontend/src/app/features/admin/admin.component.spec.ts` — cover: it
  loads and displays the current setting on init (`GET` call); changing
  it calls `PUT` and reflects the confirmed new value; a failed load/save
  shows an error state rather than a silent failure
- [X] T022 [US1] Implement `frontend/src/app/features/admin/admin.component.ts`
  and register its route (guarded by `adminGuard`) to make T021 pass
  (depends on T020, T021)

**Checkpoint**: User Story 1 is fully functional and independently
testable — SC-001, SC-002, and SC-005 all hold.

---

## Phase 4: User Story 2 - Grant an account admin access (Priority: P2)

**Goal**: An operator can promote an existing account to admin via a
CLI, without direct database access; the promotion is recorded as an
audit event.

**Independent Test**: Run the CLI against an existing account's email
and confirm it now has admin access; run it against an unknown email and
confirm a clean rejection (per spec.md's US2 acceptance scenarios).

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T023 [P] [US2] Write failing tests for `promote_to_admin()` in
  `backend/tests/integration/test_admin_repository.py` (extend, real
  Postgres) — cover: promotes an existing account (sets `is_admin =
  true`, returns its id/email); returns `None` for an email with no
  matching account; promoting an already-admin account succeeds as a
  no-op (still returns its id/email, doesn't error)
- [X] T024 [US2] Implement `promote_to_admin()` in
  `backend/src/modules/admin/repository.py` to make T023 pass (depends
  on T002, T023)
- [X] T025 [P] [US2] Write failing tests for the promotion service +
  audit logging in `backend/tests/unit/test_admin_service.py` (extend)
  — cover: `promote_account()` on success logs an `admin_granted` event
  with `promoted_user_id`/`promoted_email` (per data-model.md); on an
  unknown email, raises `ValueError` and logs nothing
- [X] T026 [US2] Implement `promote_account()` in
  `backend/src/modules/admin/service.py` to make T025 pass (depends on
  T024, T025)
- [X] T027 [US2] Implement `backend/src/modules/admin/cli.py`
  (`--promote-admin <email>`, calling `configure_logging()` at the start
  of `main()` — the first CLI in this project to do so, per
  research.md — then `promote_account()`; exit `0` on success, `1` on
  unknown email, matching `modules/ingestion/cli.py`'s argparse/exit-code
  style) (depends on T026)

**Checkpoint**: User Stories 1 AND 2 both fully functional — SC-003,
SC-004, and SC-006 all hold.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation against a running backend+frontend and
full-suite regression check

- [X] T028 [P] Run the full `quickstart.md` validation against a locally
  running backend and frontend, confirming FR-001–FR-011 / SC-001–SC-006,
  documenting results in this tasks.md file

  **Results (live-validated against a real running backend + real Postgres, 2026-08-09):**
  - Step 1 (promote to admin): CLI exited `0`, printed a success
    message, and logged an `admin_granted` event naming the promoted
    email. Confirmed.
  - Step 2 (unknown email): CLI exited `1` with a clear stderr error;
    no account created. Confirmed.
  - Step 3 (login reflects admin status): `POST /v1/auth/login`
    response's `user.is_admin` was `true` after promotion. Confirmed.
  - Step 4 (GET default): with no `app_settings` row yet,
    `GET /v1/admin/settings/log-destination` returned `200
    {"log_to_file": true}` (the `.env`-based default). Confirmed.
  - Step 5 (PUT + audit event): `PUT ... {"log_to_file": false}`
    returned `200 {"log_to_file": false}` and logged a
    `log_destination_changed` event naming the admin's user id and the
    new value. Confirmed.
  - Step 6 (non-admin rejected): a second, non-promoted account got
    `403 {"detail": "Admin access required"}` on the same GET.
    Confirmed.
  - Step 7 (takes effect next restart, not before): with the DB-backed
    setting at `false`, restarted the backend process and issued a new
    request — `backend/logs/app.log`'s file size was identical
    before and after (289362 bytes), confirming stdout-only logging
    took effect on restart per the DB value, not `.env`'s
    `LOG_TO_FILE` (which is unset, defaulting to `true`). Confirmed.
  - Step 8 (admin panel page, frontend): the Angular dev server built
    the `admin-component` chunk cleanly, and the route/guard/component
    behavior (load-and-display, change-calls-PUT-and-reflects-confirmed-value,
    non-admin never sees the route) is covered by the 4
    `admin.component.spec.ts` tests, 3 `admin.guard.spec.ts` tests, and
    2 `app.routes.spec.ts` tests, all passing. No browser automation
    tool was available in this session to interactively click through
    the page, so this specific sub-step is verified via the passing
    test suite and a clean production-style build rather than a live
    visual check.
  - Cleanup: set `log_to_file` back to `true` (feature 011's default)
    and removed the quickstart test accounts, per this doc's Cleanup
    section.
- [X] T029 Run the full backend test suite (`pytest`) and frontend test
  suite (`vitest`), confirm no regressions in previously-passing tests
  (Constitution's CI requirement). Also re-confirm, per this project's
  established CI-parity discipline: the backend unit suite still passes
  with no `.env`/env vars at all, AND `configure_logging()` still
  degrades gracefully with no Postgres reachable either (this feature's
  new failure mode, on top of the one features 010/011 already covered)

  **Results:** backend `pytest` — 218 passed. Frontend `vitest` — 79
  passed. No-`.env`/no-env-var import of `src.main` — succeeds (degrades
  to stdout-only with a warning, matching features 010/011's existing
  behavior). `DATABASE_URL` pointed at an unreachable host with `.env`
  otherwise present (simulating no Postgres reachable) — `import
  src.main` still succeeds silently, `configure_logging()`'s
  `db_log_to_file_factory` failure falls back to `Settings.log_to_file`
  with no warning, per this feature's documented silent-fallback design.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T002's migration) —
  BLOCKS both user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion
  and on `modules/admin/repository.py`/`service.py` already existing
  (T009/T011) since it adds to those same files rather than creating
  them from scratch
- **Polish (Phase 5)**: Depends on both user stories being complete

### Within Each User Story

- Tests MUST be written and confirmed failing before their corresponding
  implementation task (Constitution Principle I)
- Repository (persistence) before service (business logic + audit
  logging) before router/CLI (entry points)
- Backend before frontend within User Story 1, since the frontend calls
  the backend's real API shape

### Parallel Opportunities

- T001 and T003 (Setup, different files) can run in parallel
- T004 and T006 (Foundational tests, different files) can run in
  parallel
- Within US1: T008, T010, T012, T014, T017, T019, T021 (all test-writing
  tasks, different files) can be parallelized where their dependencies
  allow
- T028 and T029 (Polish) can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Both foundational test-writing tasks target different files:
Task: "Write failing tests for is_admin in JWT claims and require_admin in backend/tests/unit/test_security.py"
Task: "Write failing tests for is_admin flowing through login/register/refresh in backend/tests/unit/test_auth_service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks everything)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: an admin can already control the log
   destination end-to-end through the panel — the feature's actual value
5. User Story 2 (CLI promotion) is what makes User Story 1 usable by a
   real operator without direct database access — necessary for a real
   deployment, but US1 is independently demonstrable first

### Incremental Delivery

1. Setup + Foundational → `is_admin` real end-to-end, schema ready
2. Add User Story 1 → panel works, audited, access-controlled → already
   shippable (with a manually-set `is_admin` row for testing)
3. Add User Story 2 → CLI promotion → the whole feature is now usable
   without touching the database directly → ship
4. Polish → full live validation + regression check

## Notes

- [P] tasks = different files, no dependencies on each other
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group, split by conventional commit
  type (test:/feat:/chore:), per this project's established convention
- Verify each test fails before implementing the code that makes it pass
- Remember `db/init/003_admin_settings.sql` needs a fresh Postgres volume
  (or a manual run) to apply to an already-initialized local database —
  see research.md and quickstart.md's Prerequisites
