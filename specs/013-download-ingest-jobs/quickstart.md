# Quickstart: Background Download & Ingest Jobs

## Prerequisites

- Postgres running with `db/init/004_job_runs.sql` applied — if your
  local database already existed before this feature, apply it manually
  (same caveat as features 011/012's quickstarts).
- Redis running: `docker compose up -d` (now brings up `redis` alongside
  `db`).
- Backend running from `backend/` (`uvicorn src.main:app --reload`).
- The worker running from `backend/`, in a separate terminal:
  `celery -A src.worker worker --loglevel=info`.
- An admin account (`python -m src.modules.admin.cli --promote-admin you@example.com`,
  per feature 012's quickstart) and its access token.
- **Time**: a download job for a full category (e.g. `110`, ~240
  documents) takes the same ~40 minutes feature 009's own quickstart
  already documented — this feature doesn't change that pipeline's
  speed, only wraps it. The steps below validate the wrapping (status
  transitions, durable results, error/guard handling) without requiring
  a full run to finish; step 1 explicitly only needs a couple of minutes.

## Steps

1. **Trigger a download job and watch it start (FR-001, FR-003)**

   ```
   curl -s -X POST http://localhost:8000/v1/admin/jobs/download \
     -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
     -d '{"category_id": "110"}'
   ```

   **Expected**: `201`, a job record with `status: "queued"`. Within a
   few seconds (poll `GET /v1/admin/jobs`), its `status` becomes
   `"running"`, `started_at` is set, and `data/regulations/110/manifest.json`
   starts gaining entries — proving the job genuinely invoked the real
   `download_category()` (feature 009), not a stub. Let it run for a
   couple of minutes, then move on to the next steps without waiting for
   it to finish (`result` stays `null` until it does).

2. **A duplicate trigger is rejected (FR-014, SC-007)**

   ```
   curl -s -w "\nHTTP %{http_code}\n" -X POST http://localhost:8000/v1/admin/jobs/download \
     -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
     -d '{"category_id": "110"}'
   ```

   **Expected**: `409`, no second job row created — confirm via
   `GET /v1/admin/jobs` that only one `job_type: "download"` /
   `target: "110"` row is `queued`/`running`.

3. **A download job fails cleanly for an unknown category (Edge Cases, US1 Scenario 3)**

   ```
   curl -s -X POST http://localhost:8000/v1/admin/jobs/download \
     -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
     -d '{"category_id": "not-a-real-category-id"}'
   ```

   **Expected**: the job reaches `status: "failed"` (poll `GET
   /v1/admin/jobs`) with a non-null `error` explaining why, rather than
   hanging or crashing the worker.

4. **Trigger an ingest job against an already-downloaded directory (FR-002, SC-002)**

   Using whatever `data/regulations/<subfolder>/` already has a
   `manifest.json` with at least one PDF (from step 1, or a prior manual
   download):

   ```
   curl -s -X POST http://localhost:8000/v1/admin/jobs/ingest \
     -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
     -d '{"subfolder": "110", "department": "sporting"}'
   ```

   **Expected**: `201`, then within well under a minute (poll `GET
   /v1/admin/jobs`) `status: "succeeded"` with `result.ingested >= 1`.

5. **Re-running the same ingest job is idempotent (SC-005)**

   Repeat step 4's request after job 4 has finished.

   **Expected**: `201` (this is a new job, not blocked — the prior one
   is no longer `queued`/`running`), reaches `"succeeded"` with
   `result.ingested == 0` and `result.skipped` equal to however many
   documents step 4 already ingested, and `result.failed == 0`.

6. **A subfolder outside `data/regulations/` is rejected (FR-002a)**

   ```
   curl -s -w "\nHTTP %{http_code}\n" -X POST http://localhost:8000/v1/admin/jobs/ingest \
     -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
     -d '{"subfolder": "../../etc", "department": "sporting"}'
   ```

   **Expected**: `400`, no job created.

7. **A non-admin is rejected (FR-010, SC-006)**

   Repeat step 4 with a non-admin account's token.

   **Expected**: `403 Forbidden`.

8. **History survives a backend restart (FR-004, SC-003)**

   Note the `id` and `result` of the job from step 4. Restart the
   backend process (the worker can keep running). Repeat:

   ```
   curl -s http://localhost:8000/v1/admin/jobs -H "Authorization: Bearer <token>"
   ```

   **Expected**: that job's record is present with the exact same
   `result`, unchanged by the restart.

9. **A second admin sees the same history (FR-005, SC-004)**

   Promote a second account to admin, log in as it, and repeat step 8's
   request with its token.

   **Expected**: the same job records, including ones triggered by the
   first admin.

10. **Jobs view in the admin panel (US1/US2/US3, frontend)**

    Log in as an admin in the browser, navigate to the admin Jobs page.
    **Expected**: the trigger forms for both job types work end-to-end
    against steps 1–4 above; active jobs and history are both visible
    and update as jobs progress; a non-admin never sees this page.

## Cleanup

Delete any test rows from `job_runs` created by steps 2, 3, 5, and 6 if
you want a clean history for further local development; the
`data/regulations/110/` archive from step 1 can be left in place (it's
real, reusable data, same as feature 009's own quickstart leaves behind).
