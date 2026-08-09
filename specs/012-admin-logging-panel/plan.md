# Implementation Plan: Admin Logging Panel

**Branch**: `012-admin-logging-panel` | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-admin-logging-panel/spec.md`

## Summary

Adds a minimal admin capability on top of features 007/010/011: a new
`is_admin` flag on User Account (feature 007), a durable, single-value
"log destination" setting stored in Postgres that `configure_logging()`
(feature 010/011) checks at startup ahead of its existing `.env`-based
default, a backend API + Angular page for an admin to view/change that
setting, and a CLI to promote an existing account to admin. Both the
setting change and the admin promotion are recorded as log events,
matching feature 010's existing auth-event pattern.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript/Angular (frontend
— same versions as the rest of the repo)

**Primary Dependencies**: None new — `psycopg` (already used throughout
`modules/auth/`), `PyJWT` (already used for the existing `department`
claim), Angular's existing routing/guard/interceptor infrastructure from
feature 007

**Storage**: Postgres — two schema changes: `users.is_admin` (boolean
column) and a new single-row `app_settings` table holding
`log_to_file`. Both live in `db/init/`, following the existing
`001_init_schema.sql` / `002_auth_schema.sql` numbering.

**Testing**: pytest for the backend (unit with mocked
repository/security collaborators, integration against real Postgres for
the two new repository functions and the migration itself, matching
`modules/auth/`'s existing split); Vitest for the frontend page/guard,
matching feature 007's frontend tests

**Target Platform**: Same as every other feature — FastAPI backend,
Angular frontend

**Project Type**: Web application (backend + frontend), first admin-only
surface in either

**Performance Goals**: None beyond existing bars — this is a low-traffic,
operator-only surface

**Constraints**: MUST NOT require a live Postgres connection to succeed
at backend import time (`configure_logging()` runs at import time, and
CI has no Postgres service — see research.md); MUST NOT duplicate
admin-authorization logic per-route (Constitution Principle V); MUST NOT
change feature 010's log content/format beyond adding the two new event
kinds

**Scale/Scope**: One boolean setting, one boolean per-account flag, two
new backend endpoints, one CLI, one frontend page — deliberately not a
general admin framework (spec.md Assumptions)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Test-First Development**: Applies as normal — every new
  repository/service/router/CLI/frontend behavior gets a failing test
  first in `tasks.md`. PASS.
- **II. Comprehensive Unit Testing**: The new `modules/admin/repository.py`
  functions get integration tests against real Postgres (DB-touching, per
  the existing `modules/auth/repository.py` pattern); everything above
  that layer (service, router, CLI) is unit-tested with the repository
  mocked. PASS.
- **III. API Contract Consistency**: Two new endpoints, documented in
  `contracts/admin-api.md`, plus an addendum to feature 010's
  `contracts/log-schema.md`-style documentation for the two new event
  kinds this feature introduces. PASS.
- **IV. Clean Code & Readability**: Applies as normal. PASS.
- **V. Separation of Concerns**: A new, self-contained `modules/admin/`
  bounded domain (repository + service + schemas + router + CLI),
  matching every other module's shape. Admin authorization is a single
  shared `require_admin` dependency added to `core/security.py` next to
  the existing `get_current_user` — not duplicated per-route. One
  deliberate, minimal exception: `core/logging.py` (which MUST NOT import
  from `modules/admin/` — `core/` sits below `modules/` in this
  codebase's layering) gets its own tiny, read-only query against the
  `app_settings` table, separate from `modules/admin/repository.py`'s
  full read/write API used by the actual admin endpoints. This is a
  small, deliberate duplication (one `SELECT`) in exchange for not
  inverting the dependency direction — justified in research.md, not a
  gate violation. PASS.

No Complexity Tracking entries needed — the one layering nuance above is
justified inline, not a rule violation.

## Project Structure

### Documentation (this feature)

```text
specs/012-admin-logging-panel/
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
└── 003_admin_settings.sql    # NEW — users.is_admin column, app_settings table

backend/
├── src/
│   ├── core/
│   │   ├── security.py        # MODIFIED — is_admin in JWT claims, require_admin dependency
│   │   └── logging.py         # MODIFIED — optional db_log_to_file_factory param
│   ├── main.py                 # MODIFIED — wires the real db_log_to_file_factory in
│   └── modules/
│       ├── auth/
│       │   ├── repository.py   # MODIFIED — is_admin in every user SELECT/RETURNING
│       │   ├── service.py      # MODIFIED — is_admin threaded into _issue_session
│       │   └── schemas.py      # MODIFIED — is_admin on UserPublic
│       └── admin/               # NEW module
│           ├── __init__.py
│           ├── repository.py    # get/set log destination setting, promote_to_admin
│           ├── service.py       # + audit-log calls (FR-010, FR-011)
│           ├── schemas.py
│           ├── router.py        # GET/PUT /v1/admin/settings/log-destination
│           └── cli.py           # python -m src.modules.admin.cli --promote-admin <email>
└── tests/
    ├── unit/
    │   ├── test_core_security.py     # MODIFIED — require_admin, is_admin claim
    │   ├── test_core_logging.py      # MODIFIED — db_log_to_file_factory behavior
    │   ├── test_auth_service.py      # MODIFIED — is_admin flows through
    │   ├── test_admin_service.py     # NEW
    │   └── test_admin_router.py      # NEW
    └── integration/
        ├── test_admin_repository.py  # NEW — real Postgres
        └── test_admin_migration.py   # NEW — confirms 003_admin_settings.sql applies cleanly

frontend/
└── src/app/
    ├── core/auth/
    │   └── auth.service.ts     # MODIFIED — expose is_admin from the session
    └── features/
        └── admin/               # NEW feature
            ├── admin.component.ts
            └── admin.component.spec.ts
```

**Structure Decision**: Web application — mirrors feature 007's shape
exactly (new module + core security changes on the backend, new guarded
feature page on the frontend). `modules/admin/` is a new, self-contained
bounded domain per the constitution's required module shape.

## Complexity Tracking

*No violations — table intentionally omitted. See Constitution Check
above for the one deliberately-justified layering nuance (not a
violation).*
