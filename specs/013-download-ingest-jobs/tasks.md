---

description: "Task list for feature implementation"
---

# Tasks: Background Download & Ingest Jobs

**Input**: Design documents from `/specs/013-download-ingest-jobs/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required (not optional) — Constitution Principle I (Test-First
Development) is NON-NEGOTIABLE for this project: every implementation task
below has a corresponding test task that MUST be written first, confirmed
failing, then made to pass.

**Organization**: Tasks are grouped by user story (US1, US2, US3) per
spec.md's priorities.

## Path Conventions

Web application: `db/init/`, `docker-compose.yml`,
`backend/requirements.txt`, `backend/src/{core,worker.py,modules/jobs}/`,
`backend/tests/{unit,integration}/`,
`frontend/src/app/features/admin/jobs/`.

---

## Phase 1: Setup

**Purpose**: Schema, dependencies, and module scaffolding this feature needs

> **NOTE: Write T001 FIRST, confirm it FAILS, then write the migration.**

- [X] T001 [P] Write a failing integration test for the migration in
  `backend/tests/integration/test_jobs_migration.py` — cover: after
  applying `db/init/004_job_runs.sql` against a real Postgres instance,
  `job_runs` exists with the expected columns and `CHECK` constraints
  (`job_type IN ('download','ingest')`, `status IN ('queued','running','succeeded','failed')`,
  `status` defaults to `'queued'`); the `job_runs_active_target_uniq`
  partial unique index exists and genuinely enforces the guard —
  inserting two rows with the same `job_type`/`target` while both are
  `'queued'` raises a `UniqueViolation`, but inserting a third after the
  first is updated to `'succeeded'` succeeds
- [X] T002 Add `db/init/004_job_runs.sql` (`job_runs` table + the
  `job_runs_active_target_uniq` partial unique index, per data-model.md)
  to make T001 pass — apply it manually against the local dev Postgres
  container too if it isn't a fresh volume (same caveat as features
  011/012) (depends on T001)
- [X] T003 [P] Add a `redis` service to `docker-compose.yml` (an
  off-the-shelf image, matching how `db` is already defined) and start
  it (`docker compose up -d`)
- [X] T004 [P] Add `celery` and `redis` packages to
  `backend/requirements.txt` and install them into the backend venv
- [X] T005 [P] Create `backend/src/modules/jobs/__init__.py` (empty
  module init, matching every other module's pattern)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The Celery app, worker entry point, and generic
job-record persistence/listing must all exist before either job type
can be triggered or observed — both User Story 1 and User Story 2
depend on this being real, not stubbed.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T006 [P] Write failing tests for `Settings.redis_url` in
  `backend/tests/unit/test_config.py` (extend) — cover: defaults to
  `"redis://localhost:6380/0"` when `REDIS_URL` isn't set (this
  project's default Redis port — see `docker-compose.yml`'s
  `REDIS_PORT`, chosen to avoid colliding with unrelated local services
  on the default 6379); reads it from
  the environment when it is
- [X] T007 Add `redis_url` field to `backend/src/core/config.py` to make
  T006 pass (depends on T006)
- [X] T008 [P] Write failing tests for `core/celery_app.py` in
  `backend/tests/unit/test_core_celery_app.py` — cover: constructing
  the app succeeds even when `settings_factory` raises (falls back to a
  hardcoded default broker URL, no exception propagates — the same
  regression class features 010–012 already hit, per research.md); the
  app's broker/backend URL matches `Settings.redis_url` when
  `settings_factory` succeeds
- [X] T009 Implement `backend/src/core/celery_app.py`
  (`_build_celery_app(settings_factory=Settings)`, module-level
  `celery_app`) to make T008 pass (depends on T008)
- [X] T010 Create `backend/src/worker.py` (calls `configure_logging()`,
  then imports and re-exports `celery_app` from `core.celery_app`) — the
  entry point for `celery -A src.worker worker` (no dedicated test, same
  as `modules/admin/cli.py`'s argparse wrapper — validated live in
  quickstart.md instead) (depends on T009)
- [X] T011 [P] Write failing tests for job-record persistence in
  `backend/tests/integration/test_jobs_repository.py` — cover (real
  Postgres): `insert_job()` creates a row with `status="queued"` and
  returns it; inserting a second job with the same `job_type`/`target`
  while the first is still `queued`/`running` raises a
  `DuplicateJobError` (mapping the real `UniqueViolation` from
  `job_runs_active_target_uniq`); inserting again after the first
  reaches a final status succeeds; `mark_running()`/`mark_finished()`
  correctly update status, timestamps, and `result`; `list_jobs()`
  returns every job, newest first, regardless of who triggered it
- [X] T012 Implement `backend/src/modules/jobs/repository.py`
  (`insert_job`, `mark_running`, `mark_finished`, `list_jobs`,
  `DuplicateJobError`) to make T011 pass (depends on T002, T011)
- [X] T013 [P] Create `backend/src/modules/jobs/schemas.py` (`JobRecord`
  response schema, generic across job types, per
  `contracts/jobs-api.md`'s "Job record shape")
- [X] T014 [P] Write failing tests for the job list endpoint in
  `backend/tests/unit/test_jobs_router.py` — cover: `GET /v1/admin/jobs`
  returns 401 unauthenticated, 403 for a non-admin, and 200 with the
  repository's job list (mocked) for an admin, preserving its newest-first
  order
- [X] T015 Implement `GET /v1/admin/jobs` in
  `backend/src/modules/jobs/router.py` (gated by `require_admin`) and
  register the router in `backend/src/main.py` to make T014 pass
  (depends on T012, T013, T014)

**Checkpoint**: Job records can be created, persisted, listed, and
viewed by any admin. Neither job type can be triggered yet.

---

## Phase 3: User Story 1 - Trigger and monitor a download job (Priority: P1)

**Goal**: An admin triggers a download job from the panel by category
identifier and watches it move from queued to running to a final
outcome with accurate counts.

**Independent Test**: Trigger a download job for a category via the API
and confirm it reaches a final status with accurate counts,
independent of ingestion.

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T016 [P] [US1] Write failing tests for `trigger_download_job()` /
  `execute_download_job()` in `backend/tests/unit/test_jobs_service.py`
  — cover: `trigger_download_job()` inserts a job via the repository
  (mocked) with `job_type="download"`, `target=category_id`,
  `params={"category_id": ...}`, and enqueues the task (mocked enqueue
  function) with the new job's id; a `DuplicateJobError` from the
  repository propagates unchanged; if the enqueue call raises, the job
  is marked `failed` with an `error` and a clear exception is raised
  (for the router to map to 502, per research.md);
  `execute_download_job()` marks the job `running`, calls
  `download_category()` (mocked) with
  `output_dir="data/regulations/<category_id>"`, then marks it
  `succeeded` with `result` built from the returned `DownloadRunResult`'s
  downloaded/skipped/failed counts; if `download_category()` raises, the
  job is marked `failed` with the exception's message as `error`
- [X] T017 [US1] Implement `trigger_download_job()` /
  `execute_download_job()` in `backend/src/modules/jobs/service.py` to
  make T016 pass (depends on T012, T016)
- [X] T018 [P] [US1] Write failing tests for the download Celery task in
  `backend/tests/unit/test_jobs_tasks.py` — cover:
  `run_download_job_task(job_id)` calls
  `jobs_service.execute_download_job(job_id)` (mocked) — a thin wrapper
  with no independent logic (research.md)
- [X] T019 [US1] Implement `run_download_job_task` in
  `backend/src/modules/jobs/tasks.py` (`@celery_app.task`) to make T018
  pass (depends on T017, T018)
- [X] T020 [P] [US1] Write failing tests for the download trigger
  endpoint in `backend/tests/unit/test_jobs_router.py` (extend) — cover:
  `POST /v1/admin/jobs/download` returns 401/403 per the existing
  pattern; 201 with the created job record for an admin (service
  mocked); 422 for a missing `category_id`; 409 when the service raises
  `DuplicateJobError`; 502 when the service reports an enqueue failure
- [X] T021 [US1] Implement `POST /v1/admin/jobs/download` in
  `backend/src/modules/jobs/router.py` to make T020 pass (depends on
  T017, T020)
- [X] T022 [P] [US1] Write failing tests for the Jobs view in
  `frontend/src/app/features/admin/jobs/jobs.component.spec.ts` — cover:
  on init, it loads and displays jobs from `GET /v1/admin/jobs`, split
  into an active section (`queued`/`running`) and a history section
  (`succeeded`/`failed`); submitting the download trigger form (category
  identifier) calls `POST /v1/admin/jobs/download` and the new job
  appears in the active section; a failed load shows an error state
- [X] T023 [US1] Implement
  `frontend/src/app/features/admin/jobs/jobs.component.ts` (download
  trigger form + active/history list, polling `GET /v1/admin/jobs` on
  an interval while any job is active — research.md) and register its
  route (guarded by `authGuard` + `adminGuard`, per feature 012's
  pattern) to make T022 pass (depends on T021, T022)

**Checkpoint**: User Story 1 is fully functional and independently
testable — SC-001, SC-006, and SC-007 hold for download jobs.

---

## Phase 4: User Story 2 - Trigger and monitor an ingest job (Priority: P1)

**Goal**: An admin triggers an ingest job from the panel by subfolder
and department, and watches it move from queued to running to a final
outcome with accurate counts, skipping already-ingested documents.

**Independent Test**: Point an ingest job at a directory of
already-downloaded PDFs via the API (no prior panel-triggered download
job required) and confirm it reaches a final status with accurate
counts.

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T024 [P] [US2] Write failing tests for ingest subfolder validation
  in `backend/tests/unit/test_jobs_service.py` (extend) — cover: a
  subfolder that resolves inside `data/regulations/` passes; a
  subfolder containing `..` segments or an absolute path is rejected
  with a clear validation error (FR-002a)
- [X] T025 [US2] Implement the subfolder validation helper in
  `backend/src/modules/jobs/service.py` to make T024 pass (depends on
  T024)
- [X] T026 [P] [US2] Write failing tests for `trigger_ingest_job()` /
  `execute_ingest_job()` in `backend/tests/unit/test_jobs_service.py`
  (extend) — cover: `trigger_ingest_job()` rejects an invalid subfolder
  or an unsupported department before creating any job row; otherwise
  inserts a job (`job_type="ingest"`, `target=subfolder`,
  `params={"subfolder": ..., "department": ...}`) and enqueues it, with
  the same duplicate/enqueue-failure handling as T016;
  `execute_ingest_job()` marks the job `running`, reads the subfolder's
  manifest (mocked `download.repository.load_manifest`), pre-checks
  each entry's title via `ingestion.repository.title_exists` (mocked,
  per research.md) — already-ingested titles are counted as `skipped`
  without calling `ingest()`; new titles are ingested via
  `ingestion.service.ingest` (mocked) — a raised exception is recorded
  as a per-document failure and processing continues to the next
  document; marks the job `succeeded` with `result` built from the
  ingested/skipped/failed counts
- [X] T027 [US2] Implement `trigger_ingest_job()` /
  `execute_ingest_job()` in `backend/src/modules/jobs/service.py` to
  make T026 pass (depends on T017, T025, T026)
- [X] T028 [P] [US2] Write failing tests for the ingest Celery task in
  `backend/tests/unit/test_jobs_tasks.py` (extend) — cover:
  `run_ingest_job_task(job_id)` calls
  `jobs_service.execute_ingest_job(job_id)` (mocked)
- [X] T029 [US2] Implement `run_ingest_job_task` in
  `backend/src/modules/jobs/tasks.py` to make T028 pass (depends on
  T027, T028)
- [X] T030 [P] [US2] Write failing tests for the ingest trigger endpoint
  in `backend/tests/unit/test_jobs_router.py` (extend) — cover: `POST
  /v1/admin/jobs/ingest` returns 401/403 per the existing pattern; 201
  for an admin (service mocked); 422 for a missing field or unsupported
  department; 400 when the service reports an invalid subfolder
  (FR-002a); 409 for a duplicate; 502 for an enqueue failure
- [X] T031 [US2] Implement `POST /v1/admin/jobs/ingest` in
  `backend/src/modules/jobs/router.py` to make T030 pass (depends on
  T027, T030)
- [X] T032 [P] [US2] Write failing tests for the ingest trigger form in
  `frontend/src/app/features/admin/jobs/jobs.component.spec.ts` (extend)
  — cover: submitting the ingest form (subfolder + department) calls
  `POST /v1/admin/jobs/ingest` and the new job appears in the active
  section
- [X] T033 [US2] Extend
  `frontend/src/app/features/admin/jobs/jobs.component.ts` with the
  ingest trigger form to make T032 pass (depends on T023, T032)

**Checkpoint**: User Stories 1 AND 2 both fully functional — SC-002 and
SC-005 hold, and FR-002a/FR-007/FR-008 hold for ingest jobs.

---

## Phase 5: User Story 3 - Review job history across admins (Priority: P2)

**Goal**: Any admin — not just the one who triggered a job — can see
what background jobs have run, when, and with what outcome.

**Independent Test**: Trigger at least one job, restart the backend,
and confirm a different admin session can still see its full outcome.

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T034 [P] [US3] Write a failing integration test in
  `backend/tests/integration/test_jobs_service.py` (NEW — real
  Postgres, no mocks, exercising the full service layer rather than
  each layer mocked in isolation) — cover: calling
  `trigger_download_job()` attributed to one admin email and
  `trigger_ingest_job()` attributed to a different admin email, then
  `list_jobs()` returns both with correct, distinct
  `triggered_by_email` values — proving the full
  trigger→persist→list path is wired correctly end-to-end, with no job
  hidden based on who's asking (SC-004)
- [X] T035 [US3] Fix any gap T034 reveals in `trigger_download_job()` /
  `trigger_ingest_job()` / `list_jobs()` to make it pass (depends on
  T017, T027, T034)
- [X] T036 [P] [US3] Write failing tests in
  `frontend/src/app/features/admin/jobs/jobs.component.spec.ts` (extend)
  — cover: a job whose `triggered_by_email` differs from the currently
  logged-in admin's own email still renders in both the active and
  history sections — no client-side "mine only" filtering
- [X] T037 [US3] Fix
  `frontend/src/app/features/admin/jobs/jobs.component.ts` if T036
  reveals any accidental "mine only" filtering (depends on T023, T033,
  T036)

**Checkpoint**: All three user stories are independently functional —
SC-003 (restart survival) and SC-004 both hold.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation against a running backend, worker, and
frontend, plus full-suite regression check

- [X] T038 [P] Run the full `quickstart.md` validation against a
  locally running backend, worker, and frontend (with Redis via `docker
  compose up -d`), confirming FR-001–FR-014 / SC-001–SC-007,
  documenting results in this tasks.md file

  **Results (live-validated against a real running backend + worker +
  real Postgres/Redis + the real FIA site + real Ollama embeddings,
  2026-08-09):**
  - Step 1 (trigger download, watch it start): `201`, then within
    seconds `status: "running"`, `started_at` set, and
    `data/regulations/110/manifest.json` genuinely gaining entries from
    the live FIA site. Confirmed.
  - Step 2 (duplicate rejected): second trigger for the same category
    while the first was still running got `409`, no second row.
    Confirmed.
  - Step 3 (clean failure for an unknown category): reached
    `status: "failed"` with a clear `error` (a real 500 from the FIA
    API), worker kept running afterward. Confirmed.
  - Step 4 (ingest an already-downloaded directory): `201`, reached
    `status: "succeeded"` with `result.ingested: 3` (real regulation
    PDFs, real Ollama embeddings). Confirmed.
  - Step 5 (idempotent re-run): a second ingest job against the same
    subfolder (which had kept growing via the still-running download
    job) reached `succeeded` with `skipped: 3` (the 3 already-ingested
    titles) and `ingested: 18` (genuinely new ones), `failed: 0`.
    Confirmed.
  - Step 6 (path traversal rejected): `400`, no job created. Confirmed.
  - Step 7 (non-admin rejected): `403`. Confirmed.
  - Step 8 (restart survival): restarted the backend process (worker
    left running); a completed job's `result` was byte-for-byte
    unchanged afterward. Confirmed.
  - Step 9 (second admin sees the same history): a freshly-promoted
    second admin, in its own session, saw all 4 jobs triggered by the
    first admin. Confirmed.
  - Step 10 (frontend Jobs page): production-style build compiled
    cleanly with the new `jobs-component` chunk and served successfully;
    trigger-form/active-history-split/non-admin-never-sees-it behavior
    is covered by the 6 passing `jobs.component.spec.ts` tests plus the
    2 new `app.routes.spec.ts` tests for the `admin/jobs` route. No
    browser automation tool was available this session for an
    interactive click-through, same limitation noted in feature 012's
    Polish phase.
  - Cleanup: deleted all test job records, ingested test documents, and
    test accounts created during this validation; removed the
    `data/regulations/110/` archive downloaded during it (unlike
    feature 009's own quickstart, this run's corresponding DB records
    were also deleted, so leaving orphaned PDF files behind would be
    inconsistent).
  - **Bug found and fixed during this validation**: `core/celery_app.py`'s
    graceful-degradation warning (research.md) was firing through
    Python's unformatted last-resort log handler instead of this
    project's JSON pipeline, because `main.py` imported the jobs router
    (which transitively constructs `celery_app` at module import time)
    *before* calling `configure_logging()`. Fixed by moving all router
    imports (and `RequestLoggingMiddleware`) below the
    `configure_logging()` call in `main.py`, so nothing that might log
    at import time runs before the JSON formatter is attached.
- [X] T039 Run the full backend test suite (`pytest`) and frontend test
  suite (`vitest`), confirm no regressions in previously-passing tests
  (Constitution's CI requirement). Also re-confirm, per this project's
  established CI-parity discipline: the backend unit suite still passes
  with no `.env`/env vars at all, AND now also with Redis unreachable
  (this feature's new failure mode, on top of the ones features
  010–012 already covered — research.md)

  **Results:** backend `pytest` — 270 passed. Frontend `vitest` — 87
  passed. No-`.env`/no-env-var import of `src.main` — succeeds, both
  `configure_logging()`'s and `core/celery_app.py`'s fallback warnings
  now correctly JSON-formatted (see T038's bug fix above). `REDIS_URL`
  pointed at an unreachable host with `.env` otherwise present — `import
  src.main` still succeeds silently (Celery doesn't connect at
  construction time, only when a task is actually enqueued).
- [X] T040 Bump `VERSION`/`frontend/package.json`/`backend/src/__init__.py`
  and add a linked `CHANGELOG.md` entry, per the constitution's
  Development Workflow rule

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T002's migration,
  T004's `celery`/`redis` packages) — BLOCKS both user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion
  and on `modules/jobs/service.py`/`router.py`/`tasks.py` already
  existing (T017/T019/T021) since it adds to those same files rather
  than creating them from scratch
- **User Story 3 (Phase 5)**: Depends on both User Story 1 and User
  Story 2 (its tests need both `trigger_download_job()` and
  `trigger_ingest_job()` to exist) — the only story that isn't
  independent of the others, matching spec.md's own framing
- **Polish (Phase 6)**: Depends on all three user stories being
  complete

### Within Each User Story

- Tests MUST be written and confirmed failing before their
  corresponding implementation task (Constitution Principle I)
- Repository (persistence) before service (business logic) before
  tasks.py (Celery wrapper) before router (entry point) before frontend
- Backend before frontend within each user story, since the frontend
  calls the backend's real API shape

---

## Parallel Example: Foundational Phase

```bash
# These touch different files and can be written together:
Task: "Write failing tests for Settings.redis_url in backend/tests/unit/test_config.py"
Task: "Write failing tests for core/celery_app.py in backend/tests/unit/test_core_celery_app.py"
Task: "Write failing tests for job-record persistence in backend/tests/integration/test_jobs_repository.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks both stories)
3. Complete Phase 3: User Story 1 (download jobs)
4. **STOP and VALIDATE**: Trigger a download job end-to-end, confirm it
   reaches a final status with accurate counts
5. Deploy/demo if ready — download-only is already a real
   improvement over the CLI-only status quo

### Incremental Delivery

1. Complete Setup + Foundational → job records can be created, listed,
   viewed by any admin (no job type triggerable yet)
2. Add User Story 1 → download jobs work end-to-end → validate
3. Add User Story 2 → ingest jobs work end-to-end → validate
4. Add User Story 3 → confirm multi-admin visibility and restart
   survival → validate
5. Each story adds value without breaking the previous ones

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing
- Commit after each task or logical group, split by conventional type
  (feat/test/chore), per this session's established pattern
- Stop at any checkpoint to validate a story independently
