-- Background download/ingest jobs schema. Runs automatically on first
-- container startup via /docker-entrypoint-initdb.d/ for a brand-new
-- volume; on an already-initialized database, apply by hand (see
-- specs/013-download-ingest-jobs/quickstart.md Prerequisites). See
-- specs/013-download-ingest-jobs/data-model.md for the design this
-- implements.

CREATE TABLE job_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Monotonic insertion order, used only for sorting list_jobs() results
    -- newest-first. created_at (timestamptz) is NOT reliable for this:
    -- now() returns the same value for every statement within one
    -- transaction, so jobs inserted close together (or, in tests, within
    -- the same uncommitted transaction) can tie on created_at.
    seq bigserial NOT NULL,
    job_type text NOT NULL CHECK (job_type IN ('download', 'ingest')),
    target text NOT NULL,
    status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    params jsonb NOT NULL DEFAULT '{}'::jsonb,
    result jsonb,
    error text,
    triggered_by_email text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    finished_at timestamptz
);

-- Enforces FR-014: at most one active (queued/running) job per
-- job_type + target — see research.md for why this is a DB constraint
-- rather than an application-level check-then-insert.
CREATE UNIQUE INDEX job_runs_active_target_uniq
    ON job_runs (job_type, target)
    WHERE status IN ('queued', 'running');
