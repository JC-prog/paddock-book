---

description: "Task list for JWT-Based Authentication System"
---

# Tasks: JWT-Based Authentication System

**Input**: Design documents from `/specs/007-user-authentication/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/auth-api.md, quickstart.md

**Tests**: Constitution Principle I (Test-First, NON-NEGOTIABLE) applies to both backend and frontend. `security` and `service` are true unit tests with no live dependency (all collaborators mocked); `repository` and the full register→login→refresh→logout flow need a real Postgres and live in `backend/tests/integration/`, per the Principle II distinction established since feature 005. Frontend tests (Vitest) cover the auth service, interceptor, guard, and each component.

**Organization**: Tasks are grouped by user story from spec.md (US1 = P1 Login, US2 = P2 Logout, US3 = P3 Register). Login and Refresh are grouped under US1 since silent refresh-on-load is what fulfills FR-005 (session persists across reload), an explicit US1 acceptance scenario.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths are `backend/`- or `frontend/`-relative except where stated in full

---

## Phase 1: Setup

**Purpose**: Add the new backend dependencies and scaffold the auth module package

- [X] T001 [P] Add `PyJWT==2.13.0`, `bcrypt==5.0.0` to `backend/requirements.txt` (research.md)
- [X] T002 [P] Create `backend/src/modules/auth/__init__.py` (plan.md Project Structure)

**Checkpoint**: Dependencies installable, package skeleton exists.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The DB schema, JWT/password utilities, request-authentication dependency, shared schemas, and repository are used by all three user stories' service logic. None of this is story-specific.

**⚠️ CRITICAL**: No user story implementation task may start until this phase is complete.

- [X] T003 [P] Write `db/init/002_auth_schema.sql` — `users` table (`id`, `email` UNIQUE, `password_hash`, `department` reusing feature 005's enum, `created_at`) and `refresh_tokens` table (`id`, `user_id` FK `ON DELETE CASCADE`, `token_hash` UNIQUE, `created_at`, `expires_at`, `revoked_at` nullable), per data-model.md — applied manually to the already-running local database (quickstart.md step 1)
- [X] T004 [P] Extend `backend/tests/unit/test_config.py` with failing tests for `Settings.jwt_secret` (required), `Settings.access_token_ttl_minutes` (defaults to 15), `Settings.refresh_token_ttl_days` (defaults to 7) — confirmed failing before `config.py` is updated (Constitution Principle I); added an autouse `JWT_SECRET` fixture so the 4 pre-existing tests keep passing once `jwt_secret` becomes required
- [X] T005 Extend `backend/src/core/config.py`'s `Settings` with `jwt_secret`, `access_token_ttl_minutes` (default 15), `refresh_token_ttl_days` (default 7) — makes T004 pass; also added `JWT_SECRET` to `.env`/`.env.example` with a generate-a-real-secret-before-deploying note
- [X] T006 [P] Write failing unit tests in `backend/tests/unit/test_security.py` — `hash_password`/`verify_password` (bcrypt round-trip; a wrong password fails verification); `create_access_token`/`decode_access_token` (a valid token round-trips its claims — `sub`, `email`, `department`; an expired or tampered token raises); `get_current_user` FastAPI dependency (a valid `Authorization: Bearer` header resolves to the token's claims; a missing or invalid one raises 401)
- [X] T007 Implement `backend/src/core/security.py` — `hash_password`/`verify_password` (`bcrypt`); `create_access_token`/`decode_access_token` (`PyJWT`, HS256, `Settings.jwt_secret`); `get_current_user` dependency (decodes the bearer token and returns its claims directly — no DB round-trip, since department/email don't change after account creation in this feature) — makes T006 pass. Fixed a flaky tampered-token test along the way: flipping only the JWT's last base64url character can land on a bit boundary that doesn't change the decoded signature bytes, so the test now replaces the last 4 characters instead
- [X] T008 [P] Write a failing integration test in `backend/tests/integration/test_auth_repository.py` — requires the local database running; covers `create_user`/`get_user_by_email`/email-uniqueness (`users`), and `create_refresh_token`/`get_valid_refresh_token`/`revoke_refresh_token` including that a revoked or expired token is correctly excluded (`refresh_tokens`) — confirmed failing (module doesn't exist) before implementation
- [X] T009 [P] Implement `backend/src/modules/auth/schemas.py` — `RegisterRequest`, `LoginRequest`, `AuthResponse` (`access_token` + `user`), `UserPublic` (`id`, `email`, `department`), per contracts/auth-api.md. `password` is left unconstrained at the schema level (FR-012's empty-password rejection is deliberately a service-layer check, per T031/T034, not a Pydantic field constraint)
- [X] T010 Implement `backend/src/modules/auth/repository.py` — `create_user`, `get_user_by_email`, `create_refresh_token`, `get_valid_refresh_token` (excludes revoked/expired), `revoke_refresh_token` — makes T008 pass. 8/8 integration tests passing against the real local database

**Checkpoint**: Schema, config, security utilities, shared schemas, and repository all exist and are tested — every user story can now be built on top of them.

---

## Phase 3: User Story 1 - Log in to access the application (Priority: P1) 🎯 MVP

**Goal**: A staff member with valid credentials logs in and receives an authenticated session that persists across page reloads via silent refresh, per FR-001, FR-002, FR-005, FR-010 (spec.md).

**Independent Test**: Using a directly-seeded test account (no register endpoint required), submit valid credentials and confirm access is granted; submit invalid credentials and confirm a generic rejection (spec.md's own Independent Test for this story).

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (Constitution Principle I)**

- [X] T011 [P] [US1] Write failing unit tests in `backend/tests/unit/test_auth_service.py` for `login()` and `refresh_access_token()` — repository and security mocked; wrong password and unknown email both produce the same generic rejection (FR-002); valid credentials return an access token and cause a new refresh token to be created; `refresh_access_token()` rotates the refresh token (revokes the old one, creates a new one) and rejects an invalid/revoked/expired one
- [X] T012 [US1] Write failing integration test additions in `backend/tests/integration/test_auth_api.py` — real Postgres + `TestClient`; a user is seeded directly via `repository.create_user` (independent of the register endpoint, per spec.md's Independent Test); `POST /login` returns `200` with `access_token` and a `Set-Cookie` refresh cookie on success, `401` with a generic error on bad credentials; `POST /refresh` returns a new `access_token` and a rotated cookie when the refresh cookie is valid, `401` when it isn't — confirmed failing before implementation
- [X] T013 [P] [US1] Write failing Vitest tests in `frontend/src/app/core/auth/auth.service.spec.ts` — `login()` stores the access token in memory (not `localStorage`/`sessionStorage`) and exposes the current user; `refresh()` on app init silently restores a session if the refresh cookie is valid, and leaves the user logged out if it isn't
- [X] T014 [P] [US1] Write failing Vitest tests in `frontend/src/app/core/auth/auth.interceptor.spec.ts` — an outgoing request gets an `Authorization: Bearer <token>` header attached when a token is held; no header is attached when logged out
- [X] T015 [P] [US1] Write failing Vitest tests in `frontend/src/app/core/auth/auth.guard.spec.ts` — allows navigation when authenticated, redirects to `/login` when not
- [X] T016 [P] [US1] Write failing Vitest tests in `frontend/src/app/features/auth/login/login.component.spec.ts` — submitting valid credentials navigates into the app; submitting invalid credentials shows the generic error and keeps the user on the login page

### Implementation for User Story 1

- [X] T017 [US1] Implement `login()` and `refresh_access_token()` in `backend/src/modules/auth/service.py` — makes T011 pass (depends on T007, T010, T011). Required two small additions discovered mid-implementation: `generate_refresh_token`/`hash_token` in `core/security.py` (raw refresh tokens are never stored, mirroring password storage — research.md) and `repository.get_user_by_id`, both test-first
- [X] T018 [US1] Implement `POST /v1/auth/login` and `POST /v1/auth/refresh` in `backend/src/modules/auth/router.py` per contracts/auth-api.md (cookie set/read, correct status codes); include the router and add `allow_credentials=True` to the CORS middleware in `backend/src/main.py` — makes T012 pass (depends on T017, T012). **Real bug found and fixed via the integration tests**: the refresh cookie's `Secure` flag (as originally specced in contracts/auth-api.md) is silently dropped by both browsers and `TestClient` over plain `http://localhost`, breaking the whole refresh flow in local dev. Added `Settings.cookie_secure` (defaults `false`) and updated contracts/auth-api.md accordingly
- [X] T019 [P] [US1] Implement `frontend/src/app/core/auth/auth.service.ts` — makes T013 pass
- [X] T020 [P] [US1] Implement `frontend/src/app/core/auth/auth.interceptor.ts` — makes T014 pass (depends on T019)
- [X] T021 [P] [US1] Implement `frontend/src/app/core/auth/auth.guard.ts` — makes T015 pass (depends on T019)
- [X] T022 [US1] Implement `frontend/src/app/features/auth/login/login.component.ts` (+ template) — makes T016 pass (depends on T019); wire the `/login` route, register the interceptor and the guard in `app.config.ts`/`app.routes.ts`, and guard the existing chat route. Also added an `APP_INITIALIZER` that awaits the initial silent-refresh call before bootstrap completes — without it, the guard's `currentUser()` check races an in-flight refresh on a hard reload and would incorrectly bounce a genuinely logged-in user to `/login` (needed to actually satisfy FR-005/Acceptance Scenario 3, not just make the isolated unit tests pass)
- [X] T023 [US1] Manually validate Acceptance Scenarios 1–3 against a directly-seeded test account, via quickstart.md steps 4 and 6's login portion (depends on T022) — validated live: real backend + frontend dev servers, real seeded account, curl-verified login/wrong-password/refresh/no-cookie flows all correct. **Partial**: could not visually confirm the browser-side guard redirect (no JS-executing browser tool available this session) — covered instead by `auth.guard.spec.ts` (guard logic) and `app.routes.spec.ts` (wiring)

**Checkpoint**: Login is fully functional and independently testable with a seeded account.

---

## Phase 4: User Story 2 - Log out to end a session securely (Priority: P2)

**Goal**: Logging out actually revokes the session server-side, not just client-side, per FR-003 (spec.md).

**Independent Test**: Log in, then log out, then confirm the previous session can no longer be used — spec.md's own Independent Test for this story.

### Tests for User Story 2 ⚠️

- [X] T024 [P] [US2] Write failing unit tests in `backend/tests/unit/test_auth_service.py` for `logout()` — repository mocked; revokes the refresh token matching the provided cookie value; is a no-op (not an error) when no valid refresh token is provided
- [X] T025 [US2] Write failing integration test additions in `backend/tests/integration/test_auth_api.py` — real flow: login, then `POST /logout` returns `204` and clears the cookie, then a subsequent `POST /refresh` with the old cookie returns `401`
- [X] T026 [P] [US2] Write a failing Vitest test extending `frontend/src/app/shared/navbar/navbar.component.spec.ts` — a logged-in state shows a logout action; clicking it calls the auth service's logout and returns to a logged-out state

### Implementation for User Story 2

- [X] T027 [US2] Implement `logout()` in `backend/src/modules/auth/service.py` — makes T024 pass (depends on T017, T024)
- [X] T028 [US2] Implement `POST /v1/auth/logout` in `backend/src/modules/auth/router.py` per contracts/auth-api.md — makes T025 pass (depends on T027, T025)
- [X] T029 [US2] Add the logout action to `frontend/src/app/shared/navbar/navbar.component.ts` (+ template), calling `auth.service.ts`'s logout — makes T026 pass (depends on T019, T026). Also added `AuthService.logout()` itself (not a separate task, but the natural home for the HTTP call — clears client-side session state even if the backend call fails, so the UI never gets stuck "logged in" after a network blip)
- [X] T030 [US2] Manually validate Acceptance Scenarios 1–2 via quickstart.md steps 5 and 6's logout portion (depends on T028, T029) — validated live: real backend, real seeded account; logout → 204 + cookie cleared; refresh after logout → 401 (genuine revocation, not just client-side); logout with no session at all → 204 no-op, not an error

**Checkpoint**: Login and Logout are both functional and independently testable.

---

## Phase 5: User Story 3 - Register a new account (Priority: P3)

**Goal**: A new staff member can create their own account through a public registration flow, with a department assigned at creation, per FR-006, FR-007, FR-008, FR-011, FR-012 (spec.md).

**Independent Test**: Submit the registration form with an email, password, and department, then confirm the resulting account can immediately log in — spec.md's own Independent Test for this story.

### Tests for User Story 3 ⚠️

- [ ] T031 [P] [US3] Write failing unit tests in `backend/tests/unit/test_auth_service.py` for `register()` — repository and security mocked; a duplicate email is rejected before any password hashing or write happens; an empty password is rejected (FR-012); a valid submission hashes the password before it reaches the repository and assigns the given department
- [ ] T032 [US3] Write failing integration test additions in `backend/tests/integration/test_auth_api.py` — real flow: `POST /register` returns `201` with `access_token`/`user` and a refresh cookie on success; returns `422` for a duplicate email, an empty password, or an invalid department, with no row written in either case
- [ ] T033 [P] [US3] Write failing Vitest tests in `frontend/src/app/features/auth/register/register.component.spec.ts` — submitting a valid registration navigates into the app already logged in; a duplicate-email response shows a clear error and keeps the user on the registration page

### Implementation for User Story 3

- [ ] T034 [US3] Implement `register()` in `backend/src/modules/auth/service.py` — makes T031 pass (depends on T007, T010, T031)
- [ ] T035 [US3] Implement `POST /v1/auth/register` in `backend/src/modules/auth/router.py` per contracts/auth-api.md — makes T032 pass (depends on T034, T032)
- [ ] T036 [US3] Implement `frontend/src/app/features/auth/register/register.component.ts` (+ template) — makes T033 pass (depends on T019); wire the `/register` route
- [ ] T037 [US3] Manually validate Acceptance Scenarios 1–3 via quickstart.md steps 3 and 6's register portion (depends on T035, T036)

**Checkpoint**: All three stories are functional — this is the complete feature.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation

- [ ] T038 Apply `db/init/002_auth_schema.sql` to the already-running local database (quickstart.md step 1), then run the full quickstart.md validation (all steps) plus the full automated suite (`backend` unit + integration, `frontend` unit) and confirm SC-001–SC-006 are met (depends on T023, T030, T037)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion, and on User Story 1's `service.py`/`router.py`/`main.py` wiring already existing (T017/T018) since it adds to the same files rather than creating them
- **User Story 3 (Phase 5)**: Depends on Foundational phase completion, and likewise adds to User Story 1's already-existing `service.py`/`router.py`
- **Polish (Phase 6)**: Depends on all three user stories being complete

### Within Each User Story

- Tests MUST be written and FAIL before their corresponding implementation (Constitution Principle I)
- Backend service implementation before its router endpoint; router before manual validation
- Frontend `auth.service.ts` (US1) before the interceptor, guard, and any component that depends on it — the interceptor/guard/register component all import it directly

### Parallel Opportunities

- T001 and T002 (Setup) can run in parallel — different files
- T003, T004, T006, T008 (Foundational tests/schema) can run in parallel — independent files; T009 (schemas) can proceed alongside them
- T013, T014, T015, T016 (US1 frontend tests) can run in parallel — four independent files; T011 (backend service test) can proceed alongside them
- T019, once written, unblocks T020/T021 to proceed in parallel — different files, both depending only on T019

---

## Parallel Example: Foundational Phase

```bash
# These four can proceed together once Setup is done:
Task: "Write db/init/002_auth_schema.sql"
Task: "Extend backend/tests/unit/test_config.py with JWT/TTL settings tests"
Task: "Write backend/tests/unit/test_security.py"
Task: "Write backend/tests/integration/test_auth_repository.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test Login independently against a seeded account (T023)
5. Deploy/demo if ready — a staff member with a manually-seeded account can already log in and stay logged in across reloads

### Incremental Delivery

1. Complete Setup + Foundational → shared infrastructure ready
2. Add User Story 1 (Login) → test independently → deploy/demo (MVP!)
3. Add User Story 2 (Logout) → test independently → deploy/demo
4. Add User Story 3 (Register) → test independently → deploy/demo — only now does the system support onboarding new staff without manual DB seeding
5. Each story adds value without breaking the previous ones

---

## Notes

- [P] tasks = different files, no dependencies
- [US1]/[US2]/[US3] labels map every Phase 3–5 task to its spec.md story for traceability
- Verify each test fails before implementing (Constitution Principle I is NON-NEGOTIABLE for this project)
- Commit after each task or logical group, split by conventional-commit type (`feat:`, `test:`, `chore:`) rather than one combined commit
- Password reset, MFA, OAuth/social login, account deactivation, and department reassignment are explicitly out of scope (spec.md Assumptions) — do not add them here
- Do not gate any existing endpoint (health, chat, ingestion) behind `get_current_user` in this feature — none of them serve department-scoped content yet (spec.md Assumptions); this feature only delivers the reusable mechanism
- No CSRF-token scheme beyond `SameSite=Lax` (research.md) — do not add one here
