# Implementation Plan: JWT-Based Authentication System

**Branch**: `007-user-authentication` | **Date**: 2026-08-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-user-authentication/spec.md`

## Summary

Self-hosted register/login/logout for the app, backed by two new Postgres
tables (`users`, `refresh_tokens`) in the existing local database. Passwords
are hashed with `bcrypt`; login issues a short-lived JWT access token (held
in-memory by the Angular frontend, never persisted to storage) plus a
long-lived, server-tracked refresh token delivered as an httpOnly cookie —
so logout can actually revoke a session (FR-003), and the frontend can
silently re-authenticate on page reload without exposing either token to
JS-accessible storage. Every account carries exactly one department
(reusing feature 005's `department` enum), assigned by the user at
self-service registration. This is the first feature to add real HTTP
endpoints beyond health/chat, and the first real use of frontend `core/`
(guard, interceptor) alongside backend `core/security.py`.

## Technical Context

**Language/Version**: Python 3.12 (backend, unchanged); TypeScript 5.x /
Angular 18 (frontend, unchanged)

**Primary Dependencies**: `PyJWT` 2.13.0 (JWT encode/decode — MIT license,
the standard lightweight choice; no need for `python-jose`'s broader
JOSE/JWE surface when only signed JWTs are needed); `bcrypt` 5.0.0
(password hashing — Apache-2.0, used directly rather than through
`passlib`, which has seen materially less maintenance activity in recent
years); `psycopg` (existing) for transactional writes; `pydantic-settings`
(existing `core/config.py`, extended with a JWT signing secret and token
TTLs). No new frontend dependency — Angular's `HttpClient`,
`HttpInterceptorFn`, and `Router`/`CanActivateFn` guards cover everything
needed.

**Storage**: PostgreSQL (existing local database, feature 005) — two new
tables, `users` and `refresh_tokens`, in the same `public` schema as
`documents`/`document_chunks` (no schema-per-domain split; see research.md).

**Testing**: pytest — `security` (hashing, JWT encode/decode) and `service`
(orchestration) are true unit tests with all live dependencies mocked;
`repository` and a full-flow `auth_api` test both need a real Postgres and
live in `tests/integration/`, per the Constitution Principle II distinction
established since feature 005. Vitest — `auth.service`, the interceptor,
the guard, and the login/register components/forms.

**Target Platform**: Local dev environment (same as every prior feature);
eventually AWS per the constitution's stack.

**Project Type**: Web application (backend + frontend)

**Performance Goals**: Not a hard numeric target — spec's SC-001 asks for a
single successful attempt, not a latency bound; standard web-app
responsiveness is sufficient.

**Constraints**: Self-hosted, no third-party identity provider
(constitution); passwords hashed, never stored reversibly (constitution,
FR-004); logout MUST actually revoke the session, not just rely on token
expiry (FR-003) — implies server-side refresh-token tracking, not a purely
stateless JWT scheme; the access token MUST NOT be held in
JS-readable persistent storage for the same reason httpOnly cookies exist —
minimizing what a successful XSS could exfiltrate.

**Scale/Scope**: Internal tool — low tens/hundreds of accounts expected, no
scale-driven design pressure.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature | Status |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Yes — failing tests for `security`, `service` (mocked), `repository` (integration), and the full register→login→refresh→logout flow (integration) must exist before their implementations | PASS (enforced at task-generation/implementation time) |
| II. Comprehensive Unit Testing | Yes — `security`/`service` are true unit tests with no live dependency; `repository` and the full-flow API test correctly live in `tests/integration/` since they need a real Postgres | PASS |
| III. API Contract Consistency | Yes — this is the first feature adding real REST endpoints beyond health/chat (`/v1/auth/register`, `/login`, `/logout`, `/refresh`); contract documented in `contracts/auth-api.md` and kept in sync with `test_auth_api.py` | PASS |
| IV. Clean Code & Readability | Yes — no speculative abstraction: no admin/role system (registration is self-service per spec), no CSRF-token scheme beyond `SameSite=Lax` unless a future review flags a real need (research.md), no password-complexity engine (FR-012: non-empty only) | PASS |
| V. Separation of Concerns | Yes — `modules/auth/` (router/service/schemas/repository) mirrors the existing convention; the reusable JWT-verification dependency lives in `core/security.py`, matching the constitution's own named example of "security" as a `core/` concern; frontend gets its first real `core/` (guard, interceptor) alongside `features/auth/` (login/register pages) | PASS |

No violations. Complexity Tracking is not needed.

**Post-Phase 1 re-check**: research.md, data-model.md, contracts/auth-api.md,
and quickstart.md introduce no new dependency, module, or pattern beyond
what Technical Context and the table above already accounted for. The
refresh-token-rotation and httpOnly-cookie design (research.md) exists
specifically to satisfy FR-003's real-revocation requirement, not as
speculative complexity — and the explicit decision *not* to add a
CSRF-token scheme or a Postgres schema-per-domain split (research.md) is
itself Principle IV in action: each considered addition was rejected for
lacking a concrete, current need. All 5 principles remain PASS.

## Project Structure

### Documentation (this feature)

```text
specs/007-user-authentication/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
db/init/
└── 002_auth_schema.sql            # new — users, refresh_tokens tables (reuses feature 005's department enum)

backend/
├── requirements.txt               # modified — add PyJWT, bcrypt
└── src/
    ├── core/
    │   ├── config.py                # modified — add jwt_secret, access/refresh token TTL settings
    │   └── security.py               # new — password hash/verify, JWT encode/decode, get_current_user dependency
    └── modules/
        └── auth/
            ├── __init__.py
            ├── router.py              # new — POST /v1/auth/register, /login, /logout, /refresh
            ├── schemas.py              # new — request/response models
            ├── service.py               # new — orchestrates register/login/logout/refresh
            └── repository.py            # new — users/refresh_tokens table access

backend/tests/
├── unit/
│   ├── test_security.py            # new — password hashing + JWT encode/decode, no live deps
│   └── test_auth_service.py         # new — mocked repository/security collaborators
└── integration/
    ├── test_auth_repository.py       # new — real Postgres required
    └── test_auth_api.py                # new — real Postgres + TestClient, full register→login→refresh→logout flow

frontend/src/app/
├── core/                            # new folder — first real use (constitution: singleton services/interceptors/guards)
│   └── auth/
│       ├── auth.service.ts            # new — current-user state, login/register/logout/refresh calls
│       ├── auth.guard.ts               # new — route guard requiring a logged-in session
│       └── auth.interceptor.ts          # new — attaches the in-memory access token to outgoing requests
├── features/
│   └── auth/
│       ├── login/
│       │   ├── login.component.ts       # new
│       │   └── login.component.spec.ts   # new
│       └── register/
│           ├── register.component.ts     # new
│           └── register.component.spec.ts # new
├── shared/navbar/                   # modified — show logged-in state + logout action
└── app.routes.ts                    # modified — add /login, /register; guard the existing chat route
```

**Structure Decision**: Backend follows the existing `modules/<name>/`
convention (feature 003's chat module is the closest precedent: router +
service + schemas, now with a `repository.py` too since this module owns
real persistent state). `core/security.py` is new and holds the
JWT-verification dependency specifically because the constitution names
"security" as one of `core/`'s canonical cross-cutting concerns — future
endpoints (e.g. retrieval) depend on it without duplicating auth logic.
Frontend gets its first real `core/` folder (guard + interceptor are
exactly the "singleton services, interceptors, and guards" the constitution
describes for it); `features/auth/` holds the login/register pages
following the same `features/<name>/` convention as `features/chat/` and
`features/health/`. No new schema separation in Postgres — `users`/
`refresh_tokens` join `documents`/`document_chunks` in the same `public`
schema (research.md).

## Complexity Tracking

*Not applicable — the Constitution Check above has no violations to justify.*
