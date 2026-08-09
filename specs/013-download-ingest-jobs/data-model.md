# Data Model: Background Download & Ingest Jobs

## Job Run (new — `job_runs` table)

One row per triggered execution of either job type (spec.md's Job Run
entity).

| Field | Type | Notes |
|---|---|---|
| `id` | `uuid` | Primary key, `default gen_random_uuid()` (matches `users`/`refresh_tokens`). |
| `seq` | `bigserial` | Internal-only monotonic insertion order, never exposed in the API. Used for "newest first" sorting instead of `created_at` — Postgres's `now()` returns the *same* value for every statement within one transaction, so `created_at` alone can tie between jobs inserted close together. |
| `job_type` | `text` | `'download'` or `'ingest'` — `CHECK (job_type IN ('download', 'ingest'))`. |
| `target` | `text` | The category identifier (download) or `data/regulations/` subfolder name (ingest). Used, together with `job_type`, by the duplicate-job guard below. |
| `status` | `text` | `'queued'` → `'running'` → (`'succeeded'` \| `'failed'`) — `CHECK (status IN ('queued', 'running', 'succeeded', 'failed'))`. Default `'queued'`. |
| `params` | `jsonb` | Full input the admin supplied — `{"category_id": "..."}` for download, `{"subfolder": "...", "department": "..."}` for ingest. Kept separately from `target` so the department is preserved even though it isn't part of the duplicate-detection key. |
| `result` | `jsonb` | `NULL` until the job reaches a final status. Shape depends on `job_type` (see below). |
| `error` | `text` | `NULL` unless the job failed before producing any per-item results (e.g. the category doesn't exist, or the job couldn't even be enqueued — research.md). |
| `triggered_by_email` | `text` | The admin's email at trigger time, denormalized (no FK) — same reasoning as feature 012's `Admin Granted Event` recording `promoted_email` directly rather than joining. |
| `created_at` | `timestamptz` | `default now()`. When the job was triggered (queued). |
| `started_at` | `timestamptz` | `NULL` until the worker picks it up. |
| `finished_at` | `timestamptz` | `NULL` until the job reaches a final status. |

**`result` shape for a download job**:

```json
{ "downloaded": 12, "skipped": 3, "failed": 1,
  "failures": [{ "source_url": "...", "title": "...", "reason": "..." }] }
```

Mirrors `download.service.DownloadRunResult`/`DownloadFailure` (feature
009) directly — no new failure-reporting shape invented.

**`result` shape for an ingest job**:

```json
{ "ingested": 40, "skipped": 2, "failed": 1,
  "failures": [{ "title": "...", "reason": "..." }] }
```

## Duplicate-job guard

```sql
CREATE UNIQUE INDEX job_runs_active_target_uniq
    ON job_runs (job_type, target)
    WHERE status IN ('queued', 'running');
```

Enforces FR-014 atomically at the database level (research.md) — at
most one active (`queued`/`running`) job per `(job_type, target)` pair.
Once a job reaches `succeeded`/`failed`, the index no longer covers its
row, so the same target can be triggered again.

## Relationships

- `Job Run` has no foreign key to `User Account` — same reasoning as
  feature 012's audit events: who triggered it is captured as a
  denormalized `triggered_by_email` value, not a relational reference
  meant to be joined or kept in sync if the account is later renamed or
  removed.
- `Job Run` has no foreign key to any `download`/`ingestion` table —
  `modules/jobs/` composes those modules' existing public functions
  (`download_category()`, `ingest()`) but doesn't share or extend their
  storage (FR-011: this feature doesn't alter their existing behavior).
