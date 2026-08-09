# Feature Specification: Background Download & Ingest Jobs

**Feature Branch**: `013-download-ingest-jobs`

**Created**: 2026-08-09

**Status**: Draft

**Input**: User description: "Add background job infrastructure so an admin can trigger the existing FIA PDF download (feature 009) and PDF ingestion (feature 006) pipelines from the admin panel, instead of running CLIs by hand, with visibility into job status and history. Two independently-triggerable job types: a Download job (takes a regulation category ID, runs the existing download_category() pipeline) and an Ingest job (takes an output directory and a single department, reads that directory's manifest.json, and calls the existing ingest() function for every document listed there whose title hasn't already been ingested, skipping duplicates without failing the whole job — mirroring the download pipeline's continue-on-failure behavior). Jobs run via a Celery + Redis task queue (new 'worker' and 'redis' services), not in-process, chosen deliberately for learning purposes even though the current admin volume doesn't strictly require it. Every job run (regardless of type) is recorded durably in a new database table capturing its type, input parameters, status (queued/running/succeeded/failed), start/end timestamps, and per-item results (counts of downloaded/skipped/failed for download jobs; ingested/skipped/failed for ingest jobs) — so job history survives backend restarts and is visible to any admin viewing the panel, not just the one who triggered it. The admin panel gains a new view: a form to trigger a download job (category ID) or an ingest job (output directory + department), a way to see currently running/queued jobs and their live status, and a history of past runs with their outcomes. Access is admin-only, reusing the existing is_admin/require_admin authorization from feature 012. Out of scope: any change to the existing download_category()/ingest() business logic itself — this feature only adds a way to trigger and observe them asynchronously; scheduling or automatically re-running jobs on a timer; retrying a failed job automatically (an admin can simply trigger a new job); any job type beyond these two; live-streaming logs from a running job to the UI (status/counts only, not a log tail)."

## Clarifications

### Session 2026-08-09

- Q: Should an ingest job's target directory be restricted to a specific location under the app's own data folder, or can an admin point it at any filesystem path on the server? → A: Ingest jobs may only target subdirectories of `data/regulations/` — the admin supplies a category/subfolder name, not a full path, and the system rejects anything that resolves outside it.
- Q: If two jobs are triggered against the same target at the same time (e.g. two ingest jobs on the same subfolder), should the system block the second one, or let both run concurrently? → A: Block a duplicate — reject triggering a new job while an identical one (same type and same target) is already queued or running.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trigger and monitor a download job (Priority: P1)

An admin wants to pull the latest regulation PDFs for a category without SSHing into the server and running a script by hand. From the admin panel, they enter a regulation category identifier and start a download job. The job runs in the background; the admin can watch it move from queued to running to a final outcome, and see how many documents were downloaded, skipped (already had them), and failed.

**Why this priority**: This is the first half of closing the loop between "regulations changed" and "the knowledge base has them" — without it, downloading still requires manual CLI access, which is the exact friction this feature exists to remove.

**Independent Test**: Can be fully tested by triggering a download job for a category from the panel and confirming it reaches a final status with accurate counts, independent of whether any ingestion ever happens.

**Acceptance Scenarios**:

1. **Given** an admin is viewing the panel, **When** they submit a category identifier to start a download job, **Then** a new job appears with status "queued" and then progresses to "running" without the admin's request hanging or timing out.
2. **Given** a download job has finished successfully, **When** the admin views it, **Then** its status shows "succeeded" along with counts of documents downloaded, skipped, and failed.
3. **Given** a download job encounters an unrecoverable error before completing any work (e.g. the category doesn't exist), **When** the admin views it, **Then** its status shows "failed" with enough detail to explain why.

---

### User Story 2 - Trigger and monitor an ingest job (Priority: P1)

An admin wants to feed a directory of already-downloaded PDFs into the searchable knowledge base without running the ingestion CLI by hand for every file. From the admin panel, they specify which subfolder of the app's regulation archive to ingest and pick a single department that applies to everything in it, and start an ingest job. The job runs in the background, skipping any document already in the knowledge base, and the admin can watch it reach a final outcome with accurate counts.

**Why this priority**: This is the second half of closing the loop — without it, admins still have to manually run the ingestion CLI per file, which is exactly the friction this feature exists to remove. It's equally load-bearing to User Story 1 since download alone doesn't get anything into the knowledge base.

**Independent Test**: Can be fully tested by pointing an ingest job at a directory of already-downloaded PDFs (with no prior admin panel download job required) and confirming it reaches a final status with accurate ingested/skipped/failed counts.

**Acceptance Scenarios**:

1. **Given** an admin is viewing the panel, **When** they submit a directory and a department to start an ingest job, **Then** a new job appears with status "queued" and then progresses to "running".
2. **Given** an ingest job processes a directory where some documents were already ingested previously, **When** the job finishes, **Then** those documents are counted as skipped, not as failures, and the job still reaches "succeeded".
3. **Given** an ingest job processes a directory where one document fails (e.g. it can't be parsed), **When** the job finishes, **Then** that document is recorded as a failure with a reason, the rest of the directory is still processed, and the job still reaches a final status rather than aborting.

---

### User Story 3 - Review job history across admins (Priority: P2)

Any admin — not just the one who triggered a job — wants to see what background jobs have run, when, and with what outcome, including after the backend has been restarted since a job finished.

**Why this priority**: This delivers the multi-admin visibility that's the whole point of tracking jobs durably rather than only showing status to whoever triggered them; it's valuable on its own but depends on User Story 1 and/or 2 having produced at least one job to look at.

**Independent Test**: Can be fully tested by triggering at least one job, restarting the backend, and confirming a different admin session can still see that job's full outcome in the history view.

**Acceptance Scenarios**:

1. **Given** at least one job has completed, **When** any admin opens the job history view, **Then** they see it listed with its type, status, and outcome — regardless of which admin triggered it.
2. **Given** a job completed before the backend was last restarted, **When** an admin views job history after the restart, **Then** that job's record and outcome are unchanged.

---

### Edge Cases

- What happens when an ingest job's target directory has no manifest (nothing downloaded there yet, or an unrelated directory)? The job completes with zero documents processed rather than erroring.
- What happens when an admin supplies a subfolder name that would resolve outside `data/regulations/` (e.g. containing `..` or an absolute path)? The trigger is rejected outright and no job is created.
- What happens when a job is triggered against the same target as one already queued or running (e.g. two ingest jobs pointed at the same subfolder)? The second trigger is rejected outright and no duplicate job is created; the admin can retry once the in-flight job reaches a final status.
- What happens if the background worker process crashes or is restarted while a job is "running"? That job's record may remain "running" indefinitely; this feature does not attempt to automatically detect or reconcile such stuck jobs.
- What happens when a non-admin account attempts to trigger a job or view job status/history? The action is rejected the same way other admin-only actions are (per feature 012's existing authorization).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow an admin to trigger a download job by supplying a regulation category identifier.
- **FR-002**: System MUST allow an admin to trigger an ingest job by supplying a subfolder name under the app's regulation archive (`data/regulations/`) and a single department, applied uniformly to every document that job ingests.
- **FR-002a**: System MUST reject an ingest job trigger whose supplied subfolder would resolve outside `data/regulations/` (e.g. via `..` path segments or an absolute path), without starting a job.
- **FR-003**: System MUST process both download and ingest jobs asynchronously in the background — triggering a job MUST NOT require the admin to keep a request open or wait for the job to finish.
- **FR-004**: System MUST record every job run durably (type, input parameters, status, start/end timestamps, per-item result counts) such that this history survives a backend restart.
- **FR-005**: System MUST let any admin view a job's current status and results, not only the admin who triggered it.
- **FR-006**: System MUST let an admin view a history of past job runs of both types, with their outcomes.
- **FR-007**: An ingest job MUST skip any document whose title has already been ingested, counting it as skipped rather than causing the job to fail.
- **FR-008**: An ingest job MUST continue processing the remaining documents in its target after an individual document fails, recording that failure with a reason, rather than aborting the whole job.
- **FR-009**: A download job MUST preserve the existing download pipeline's behavior of skipping already-downloaded documents and continuing past individual failures.
- **FR-010**: System MUST restrict triggering jobs and viewing job status/history to admin accounts only, reusing the existing admin authorization.
- **FR-011**: System MUST NOT alter the existing download or ingestion business logic itself — this feature only adds a way to trigger and observe that existing logic asynchronously.
- **FR-012**: System MUST NOT automatically retry a failed job or automatically re-run any job on a schedule.
- **FR-013**: System MUST record which admin triggered each job, as part of that job's durable record.
- **FR-014**: System MUST reject triggering a new job of a given type against a target (category identifier, or subfolder) that already has a job of that same type and target in "queued" or "running" status, without creating a duplicate job.

### Key Entities *(include if feature involves data)*

- **Job Run**: One triggered execution of either a download or an ingest job. Tracks: job type (download or ingest); the input parameters used to trigger it (category identifier, or `data/regulations/` subfolder name plus department); status (queued, running, succeeded, or failed); when it started and finished; per-item result counts (downloaded/skipped/failed for a download job, ingested/skipped/failed for an ingest job); and which admin triggered it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An admin can trigger a download job from the panel and watch it reach a final status with accurate counts, without needing any access to the server outside the panel itself.
- **SC-002**: An admin can trigger an ingest job from the panel and watch it reach a final status with accurate counts, without needing any access to the server outside the panel itself.
- **SC-003**: 100% of previously completed job records remain visible with unchanged, accurate outcomes after a backend restart.
- **SC-004**: A second admin who did not trigger a given job can see its full status and outcome without asking the triggering admin.
- **SC-005**: Re-running an ingest job against a directory that has already been fully ingested completes with zero newly-ingested documents and zero failures.
- **SC-006**: 100% of attempts by non-admin accounts to trigger a job or view job status/history are rejected.
- **SC-007**: 100% of attempts to trigger a job that duplicates an already in-flight job (same type, same target) are rejected without creating a second job record.

## Assumptions

- The existing `download_category()` and `ingest()` functions (features 009 and 006) are reused unchanged as the actual work each job type performs; this feature only adds a way to trigger and observe them.
- A single job processes its work sequentially, the same way the underlying pipeline already does today (page-by-page for download, document-by-document for ingest); this feature does not add parallelism within one job.
- Jobs of different types, or the same type against different targets, may run concurrently without restriction; only an exact duplicate (same type, same target) already in flight is blocked.
- If the background worker crashes or restarts mid-job, that job's record may be left in a "running" state indefinitely; automatically detecting or reconciling such stuck jobs is out of scope.
- Ingest jobs use the existing three departments established by the ingestion pipeline (sporting, technical, financial); an ingest job does not support mixing departments within a single run.
- Only existing admin accounts (per feature 012) can trigger jobs or view job status/history; there is no separate permission level within "admin" for this feature.
