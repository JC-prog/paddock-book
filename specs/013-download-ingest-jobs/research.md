# Research: Background Download & Ingest Jobs

## Celery app construction must not require a live Redis connection

**Decision**: `core/celery_app.py` builds its `Celery(...)` instance from
`Settings().redis_url`, wrapped in the same try/except-and-degrade
pattern established in `core/logging.py::configure_logging()` (features
010/011/012) — if `Settings()` itself can't be constructed (no `.env`,
missing required fields), fall back to a hardcoded default broker URL
rather than raising, so importing `src.main` (and therefore `src.core.celery_app`,
which it imports to enqueue tasks) still succeeds.

**Rationale**: `Celery(broker=..., backend=...)` does not connect to the
broker at construction time — connections are opened lazily, on the
first `.delay()`/`.send_task()` call — so constructing the app object
itself is safe even with no reachable Redis. The risk this project has
hit three times now (features 010, 011, 012) is a different one:
`Settings()` itself raising because no `.env` exists at all (this
project's actual CI has neither `.env` nor a Postgres service, confirmed
by reading `ci.yml` directly — and now, for this feature, no Redis
service either). Import-time construction of `celery_app` must survive
that, exactly like `configure_logging()` already does. This gets
explicitly re-verified in Polish (mirroring the now-established
no-`.env` CI-parity check), extended to also confirm `import src.main`
succeeds with Redis unreachable.

**Alternatives considered**: Constructing the Celery app lazily on first
use (a getter function instead of a module-level singleton) — rejected
as unnecessary complexity; Celery's own laziness about broker
connections already gives us the property we need without an extra
layer.

## Enqueuing a task when Redis is unreachable

**Decision**: Unlike app construction, `.delay()` calls a *live*
connection at request time. `modules/jobs/service.py`'s trigger
functions call it inside a try/except; on failure, the just-inserted
`job_runs` row is updated to `status="failed"` with a clear `error`
message (e.g. `"could not enqueue: <reason>"`) and committed, and the
router surfaces a `502 Bad Gateway` to the admin — a clear, immediate
failure rather than a job silently stuck in `"queued"` forever.

**Rationale**: A job that can never run because the broker was
unreachable at trigger time is a real, observable failure the admin
needs to see immediately, not discover later by noticing a job that
never progresses. Marking it `failed` immediately (rather than leaving
it `queued`) also keeps it out of the way of FR-014's duplicate-job
guard, which only blocks on `queued`/`running` rows.

## Duplicate-job guard is a Postgres partial unique index, not an app-level check

**Decision**: `job_runs` gets a partial unique index —
`UNIQUE (job_type, target) WHERE status IN ('queued', 'running')` — and
the repository's insert function catches the resulting `UniqueViolation`
and reports it as a `DuplicateJobError`, which the router maps to `409
Conflict`.

**Rationale**: A "check for an existing active job, then insert if none
found" done in two separate application-level steps has a race window —
two admins (or the same admin double-clicking) could both pass the
check before either insert commits. A partial unique index makes the
database enforce the invariant atomically, the same pattern feature
012's `app_settings` table already uses (a `CHECK (id = 1)` constraint,
not just application discipline) for a different single-row invariant.

**Alternatives considered**: A Postgres advisory lock held for the
duration of the trigger request — rejected as more moving parts for the
same guarantee a unique index already gives for free.

## Ingest job duplicate-title detection: pre-check, not exception-message matching

**Decision**: The ingest job's per-document loop calls
`ingestion.repository.title_exists(conn, title)` itself before calling
`ingestion.service.ingest(...)`, and counts an already-existing title as
skipped without calling `ingest()` at all. Any exception `ingest()` does
raise (unsupported department, parse failure, embedding failure, write
failure) is recorded as a genuine per-document failure.

**Rationale**: `ingest()` (feature 006) raises a generic `ValueError`
for both "duplicate title" and "unsupported department," distinguished
only by its message text. Matching on that string to decide
skipped-vs-failed would be fragile and would silently break if that
message ever changed. Pre-checking `title_exists()` — a function
`ingest()` already calls internally, so this doesn't change its
behavior (FR-011) — gives an unambiguous, structural way to tell "already
have this" (skip) apart from "something went wrong" (fail).

## A download job's output directory is always `data/regulations/<category_id>`

**Decision**: The admin panel's download trigger only takes a category
identifier, not a custom output directory override (unlike the existing
CLI, which accepts `--output-dir`). The job always saves to
`data/regulations/<category_id>` — the CLI's own default.

**Rationale**: This keeps a download job's `target` (the category
identifier) directly usable as an ingest job's `target` (the
`data/regulations/` subfolder name) — an admin who downloads category
`110` ingests it by supplying `110`, with no separate directory to look
up or transcribe. It also avoids introducing a second,
independently-validated path-traversal surface on the download side
(FR-002a only needed for ingest jobs) for a capability (arbitrary output
directories) the CLI's own operators have never actually needed to use
outside their default.

**Alternatives considered**: Exposing the CLI's `--output-dir` override
in the trigger form too — rejected per spec.md's Assumptions (this
feature adds a way to trigger the existing pipelines, not a more
general or more flexible version of them).

## One list endpoint serves both "current jobs" and "history"

**Decision**: A single `GET /v1/admin/jobs` returns every job run,
newest first; the frontend splits it into an "active" section
(`queued`/`running`) and a "history" section (`succeeded`/`failed`)
client-side. There's no separate `GET /v1/admin/jobs/{id}`.

**Rationale**: FR-005 (view a job's current status) and FR-006 (view
history) are two views over the same underlying data, not two different
queries — spec.md doesn't call for filtering, pagination, or a
detail view beyond what a job's own record already contains. One
endpoint keeps the contract as small as the two capabilities it actually
needs to support, matching feature 012's "one setting, not a general
settings API" precedent.

## The admin panel polls for status; it does not stream live updates

**Decision**: The frontend's Jobs view polls `GET /v1/admin/jobs` on a
fixed interval while any job is active, rather than opening a live
connection (SSE or WebSocket) for push updates.

**Rationale**: `sse-starlette` already exists in this codebase (feature
003, for chat token streaming), but that's a fundamentally different
shape of problem — a single user watching one in-flight response,
versus an occasional admin action checked back on periodically. Spec.md
explicitly scopes out live log streaming; extending that same "no live
stream" reasoning to status polling too keeps this feature's real-time
plumbing proportionate to an internal, low-traffic admin surface, not
the product's core chat path.

**Alternatives considered**: Reusing the existing SSE infrastructure for
job status push updates — rejected as disproportionate complexity (a
long-lived connection per admin browser tab, kept in sync with Celery
task state) for a capability polling already satisfies at this traffic
level.

## The worker runs as a local process, not a Docker container

**Decision**: `docker-compose.yml` gains only a `redis` service (an
off-the-shelf image, like `db` already is). The Celery worker itself
runs the same way the backend and frontend already do in local
development — as a plain process (`celery -A src.worker worker`) from
the backend's virtualenv — not as a new Dockerized service.

**Rationale**: This project has no `Dockerfile` for the backend at all
today (confirmed by inspecting the repo directly) — only Postgres is
containerized, and the backend/frontend both run as local venv/npm
processes per `README.md`. Introducing a backend container image, purely
to run the worker, would be a disproportionate new piece of
infrastructure for this feature to carry, and would diverge from how
every other process in this project is actually run today.

**Alternatives considered**: Writing a backend `Dockerfile` and adding a
`worker` service to `docker-compose.yml` — rejected for now as
out-of-proportion scope creep; revisit if/when the backend itself gets
containerized for other reasons.

## Redis holds no application state

**Decision**: Redis is used exclusively as Celery's broker and result
backend. `job_runs` in Postgres remains the single source of truth for
status and history (FR-004's durability requirement); nothing reads job
status from Redis or Celery's own result backend.

**Rationale**: Celery's result backend is inherently ephemeral/best-effort
and not what FR-004 asks for ("survives a backend restart," implying
Postgres, which this project already treats as its durable store
everywhere else). Keeping Redis purely as plumbing, not a second source
of truth, avoids a consistency problem between two stores.
