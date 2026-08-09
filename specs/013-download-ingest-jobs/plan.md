# Implementation Plan: Background Download & Ingest Jobs

**Branch**: `013-download-ingest-jobs` | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-download-ingest-jobs/spec.md`

## Summary

Adds a Celery + Redis-backed background job system so an admin can
trigger the existing FIA PDF downloader (feature 009) and PDF ingestion
pipeline (feature 006) from the admin panel instead of running their
CLIs by hand. A new `modules/jobs/` bounded domain wraps both existing
pipelines as thin, testable service functions invoked by Celery tasks; a
new `job_runs` table durably records every run (type, target, status,
timestamps, per-item results, triggering admin) so status and history
survive backend restarts and are visible to every admin, not just the
one who triggered it. The admin panel gains a new Jobs view: trigger
forms for both job types, and a polled list showing active jobs and
history.

## Technical Context

**Language/Version**: Python 3.12 (backend, worker), TypeScript/Angular
(frontend — same versions as the rest of the repo)

**Primary Dependencies**: `celery` and `redis` (new — the task queue and
its broker/result backend); reuses `download.service.download_category()`
(feature 009), `ingestion.service.ingest()` (feature 006),
`download.repository.load_manifest()` (feature 009), and
`core/security.py::require_admin` (feature 012) unchanged

**Storage**: Postgres — one new table, `job_runs` (see data-model.md);
Redis — new, used only as Celery's broker/result backend, not as
application state (Postgres remains the source of truth for job
status/history per spec.md's FR-004)

**Testing**: pytest for the backend — unit tests for `modules/jobs/service.py`
with the repository and enqueue function mocked (matching every other
module's DI pattern), integration tests for `modules/jobs/repository.py`
and the migration against real Postgres; Celery task functions themselves
are two-line wrappers with no independent logic to unit test beyond
"calls the service function," so they're covered by the live quickstart
validation instead, not a mocked-Celery unit test. Vitest for the new
frontend Jobs view.

**Target Platform**: Same as every other feature — FastAPI backend
(now also enqueues to Celery), a new Celery worker process, Angular
frontend. Following this project's existing pattern (only Postgres is
containerized; the backend and frontend run as local processes — see
research.md), the worker also runs as a local process, not inside
Docker; only Redis joins `docker-compose.yml` as a new service.

**Project Type**: Web application (backend + frontend) plus a new
background worker process — first non-request-driven, long-running
process in this project

**Performance Goals**: None beyond existing bars — this is a low-traffic,
operator-only surface; the underlying pipelines' own rate limits
(feature 009's 10s crawl delay) are unchanged and dominate job duration

**Constraints**: MUST NOT require a live Redis connection to succeed at
backend import time — the FastAPI process constructs the Celery app to
enqueue tasks, and CI has no Redis service, so this repeats (and must
pass) this project's established CI-parity discipline (features
010/011/012) for a new dependency (research.md); MUST NOT change
`download_category()`'s or `ingest()`'s existing behavior (FR-011); MUST
NOT duplicate admin-authorization logic per-route (Constitution
Principle V, reuses `require_admin`); an ingest job's target MUST be
confined to `data/regulations/` (FR-002a)

**Scale/Scope**: Two job types, one new table, one new backend module,
one new frontend view — deliberately not a general-purpose task-queue
framework (spec.md Assumptions)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Test-First Development**: Applies as normal — every new
  repository/service/router/task behavior gets a failing test first in
  `tasks.md`. PASS.
- **II. Comprehensive Unit Testing**: `modules/jobs/repository.py` gets
  integration tests against real Postgres (DB-touching, per the existing
  `modules/admin/repository.py` pattern); `modules/jobs/service.py` is
  unit-tested with the repository and the Celery enqueue call both
  mocked, so no test in the unit suite touches Redis or Postgres. PASS.
- **III. API Contract Consistency**: New endpoints documented in
  `contracts/jobs-api.md`. PASS.
- **IV. Clean Code & Readability**: Applies as normal. PASS.
- **V. Separation of Concerns**: A new, self-contained `modules/jobs/`
  bounded domain (repository + service + schemas + router + tasks),
  matching every other module's shape. It depends on
  `modules/download/` and `modules/ingestion/`'s existing public service
  functions — a modules-to-modules dependency, which the constitution's
  layering rule doesn't forbid (only `core/` importing from `modules/`
  is forbidden). The new `core/celery_app.py` is cross-cutting
  infrastructure (like `core/db.py`), not a bounded domain, so it lives
  in `core/`. PASS.

No Complexity Tracking entries needed — see research.md for the two
deliberate scope-fit decisions (worker runs as a local process, not
Dockerized; Redis holds no application state) made to keep this
feature's footprint proportionate to this project's actual current
infrastructure maturity.

## Project Structure

### Documentation (this feature)

```text
specs/013-download-ingest-jobs/
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
└── 004_job_runs.sql          # NEW — job_runs table, partial unique index for FR-014

docker-compose.yml             # MODIFIED — new `redis` service

backend/
├── requirements.txt           # MODIFIED — celery, redis
├── src/
│   ├── core/
│   │   ├── config.py          # MODIFIED — redis_url setting
│   │   └── celery_app.py      # NEW — Celery app instance (import-time-safe, see research.md)
│   ├── worker.py               # NEW — `celery -A src.worker worker` entry point;
│   │                           #        configures logging, then re-exports celery_app
│   └── modules/
│       └── jobs/                # NEW module
│           ├── __init__.py
│           ├── repository.py    # job_runs CRUD, duplicate-detection insert
│           ├── service.py       # trigger_*_job(), execute_*_job() — the real logic
│           ├── schemas.py
│           ├── router.py        # POST/GET /v1/admin/jobs...
│           └── tasks.py         # @celery_app.task wrappers calling service.execute_*_job()
└── tests/
    ├── unit/
    │   ├── test_jobs_service.py   # NEW
    │   └── test_jobs_router.py    # NEW
    └── integration/
        ├── test_jobs_repository.py  # NEW — real Postgres, incl. duplicate-index behavior
        └── test_jobs_migration.py   # NEW — confirms 004_job_runs.sql applies cleanly

frontend/
└── src/app/features/admin/
    └── jobs/                     # NEW
        ├── jobs.component.ts
        └── jobs.component.spec.ts
```

**Structure Decision**: Web application — mirrors feature 012's shape
(new self-contained module + new guarded frontend view), plus one new
process kind (the Celery worker) that this project hasn't had before.
`modules/jobs/` is a new bounded domain per the constitution's required
module shape; it composes `modules/download/` and `modules/ingestion/`
rather than duplicating their logic (FR-011).

## Complexity Tracking

*No violations — table intentionally omitted.*
