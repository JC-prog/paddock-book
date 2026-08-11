# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
This file is maintained by hand — update it alongside each version bump in
`VERSION` (see `README.md`); no `/speckit-*` command updates it automatically.
Each entry below corresponds to the spec-kit feature of the same number
under `specs/`.

## [Unreleased]

## [0.14.0] - 2026-08-11

Spec: `specs/015-download-progress-bar/spec.md`

### Added

- Backend: the FIA regulation PDF download CLI (`python -m
  src.modules.download.cli`) now shows real-time progress instead of
  printing nothing until the whole run finishes. A separate, upfront
  counting pass walks every listing page once to establish a true
  bounded total (X of Y documents) before downloading starts — kept
  deliberately separate from the existing download pass so a listing
  page failure during download still leaves everything downloaded so
  far intact (feature 009's resilience guarantee, unchanged). Renders
  as a live `tqdm` bar in an interactive terminal, or throttled
  plain-text status lines (one per 10% of progress, failures shown
  immediately) when output is redirected to a file — never raw
  escape-code spam either way.

## [0.13.0] - 2026-08-09

Spec: `specs/014-rag-eval-harness/spec.md`

### Added

- Backend: a new `modules/eval/` CLI (`python -m src.modules.eval.cli
  generate|run`) to measure the RAG pipeline's own quality — synthesizes
  a fixed, reusable set of test questions from currently-ingested
  content via an LLM, then replays that fixed set through the real,
  unmodified chat retrieval and generation pipeline, scoring retrieval
  (Hit Rate@k, MRR) and answer correctness (LLM-as-judge, excluding
  failed judgments from the accuracy metric) into a saved markdown
  report. Reports and eval sets are timestamped files, never
  overwritten, so a naive-RAG baseline report can be compared against a
  future retrieval-improvement (e.g. reranking) report over the
  identical question set.

### Fixed

- `.gitignore`'s `/data/` entry never actually matched
  `backend/data/regulations/` (it was anchored to the repo root, but
  every CLI in this project runs with `backend/` as its working
  directory) — corrected to `/backend/data/`, also covering this
  feature's new `backend/data/eval/`.

## [0.12.0] - 2026-08-09

Spec: `specs/013-download-ingest-jobs/spec.md`

### Added

- Backend: a new `modules/jobs/` domain lets an admin trigger the
  existing FIA PDF downloader (feature 009) and PDF ingestion pipeline
  (feature 006) as background jobs instead of running their CLIs by
  hand — a download job (by category) and an independently-triggerable
  ingest job (by `data/regulations/` subfolder + department), both
  composing those pipelines' existing functions unchanged.
- Backend: jobs run via a new Celery + Redis task queue (`redis`
  service in `docker-compose.yml`, a new `backend/src/worker.py` entry
  point) — the project's first background-worker process. Every job run
  is recorded durably in a new `job_runs` table (type, target, status,
  timestamps, per-item results, triggering admin), so status and
  history survive backend restarts and are visible to every admin, not
  only the one who triggered it. A partial unique index blocks
  triggering a duplicate job against the same type/target while one is
  already queued or running.
- Backend: an ingest job's target subfolder is confined to
  `data/regulations/` and rejects anything that would resolve outside
  it; already-ingested titles are skipped rather than failing the job,
  matching the download pipeline's existing continue-on-failure
  behavior.
- Frontend: a new admin-only Jobs page (`/admin/jobs`) to trigger both
  job types and see active jobs and history, polling for updates.

## [0.11.0] - 2026-08-09

Spec: `specs/012-admin-logging-panel/spec.md`

### Added

- Backend: a new `is_admin` flag on accounts (default `false`), a
  `require_admin` authorization dependency, and a small CLI
  (`python -m src.modules.admin.cli --promote-admin <email>`) — the
  only way to grant admin access, since there's no in-app or
  self-service path.
- Backend: `GET`/`PUT /v1/admin/settings/log-destination`, admin-only,
  backed by a new single-row `app_settings` table — lets an operator
  toggle between feature 011's local file logging and stdout-only
  (what production CloudWatch capture relies on), durably, without
  editing `.env`. Both the setting change and each admin promotion are
  recorded as audit log events (`log_destination_changed`,
  `admin_granted`).
- Backend: `configure_logging()` now optionally reads this DB-backed
  setting at startup (via a small, intentionally separate query in
  `main.py`, not a `modules/admin/` import — preserving the
  `core/`→`modules/` layering rule) and falls back silently to the
  `.env`-based default if no row exists yet or the database isn't
  reachable.
- Frontend: an admin-only panel (route-guarded by a new `adminGuard`,
  mirroring the existing `authGuard`) to view and change the log
  destination setting. The change takes effect on the backend's next
  restart, not live.

## [0.10.0] - 2026-08-09

Spec: `specs/011-log-file-persistence/spec.md`

### Added

- Backend: logs (feature 010's JSON format, unchanged) are now also
  persisted to a size-rotated file on disk (`logs/app.log` by default,
  10 MB x 5 backups, 60 MB hard cap), in addition to stdout — toggleable
  via `Settings.log_to_file` (on by default), so a future admin panel has
  a concrete switch to drive rather than needing this mechanism rebuilt.
- Backend: any failure to set up the file destination — missing
  directory, no permission, or even a failure to read settings at all —
  degrades to stdout-only logging with a clear warning, never blocking
  app startup or failing a request.

## [0.9.0] - 2026-08-08

Spec: `specs/010-app-logging/spec.md`

### Added

- Backend: structured JSON logging for every request — method, path,
  status, and duration, each tagged with a unique correlation ID shared
  by every log line produced while handling that request. An unhandled
  error is logged with a full stack trace while the client still gets a
  clean HTTP error response, not a hang.
- Backend: authentication events (login success/failure, logout,
  registration) and successful chat retrievals are now logged, each
  naming the account (and, for chat, the department) involved — never a
  password, token, or the question/answer text itself.
- Backend: `logout()` now looks up which account a refresh token belongs
  to before revoking it, so the logout event can name who logged out.

## [0.8.0] - 2026-08-08

Spec: `specs/009-fia-pdf-download/spec.md`

### Added

- Backend: a locally-invoked CLI
  (`python -m src.modules.download.cli --category <id> [--output-dir <path>]`)
  that downloads every regulation PDF listed in a paginated FIA regulation
  category — including superseded issues, not just the latest — saving
  each alongside a metadata record (title, source URL, section, issue/
  revision, publish date, download timestamp) in a `manifest.json`.
- Backend: re-running the tool skips any document already present in the
  manifest, so a re-run only fetches what's new. Every request to the
  source site is rate-limited to its published 10-second crawl-delay.
  A document that fails to download doesn't abort the run — it's recorded
  and reported, and the run continues.

## [0.7.0] - 2026-08-07

Spec: `specs/008-add-chatbot/spec.md`

### Added

- Backend: `POST /v1/chat` now generates a real, retrieval-grounded answer
  instead of the fixed placeholder reply (feature 003) — the question is
  embedded, the most relevant regulation chunks are retrieved from the
  pgvector store (feature 006), scoped to the requesting staff member's
  department (feature 007), and an answer is generated from them via the
  configured LLM provider (Ollama for local development; Bedrock for
  production).
- Backend: when a staff member's department has no ingested content at
  all, the endpoint deterministically responds that it has no relevant
  information rather than attempting to generate a guess; when content is
  retrieved but doesn't actually answer the question, the model is
  instructed to say the same, on a best-effort (not guaranteed) basis.
- Backend: `POST /v1/chat` now requires a logged-in session (feature 007)
  — an unauthenticated request is rejected rather than producing any
  answer. A retrieval or embedding failure (e.g. the LLM provider or
  database is unreachable) returns a clean `502` before any response
  stream opens, rather than breaking an already-open connection.
- Backend: `core/embeddings.py` — the Bedrock Titan V2 embedding call,
  promoted out of the ingestion module (feature 006) since retrieval is
  now a second real consumer of it.
- Frontend: the chat request now attaches the logged-in staff member's
  access token, so questions reach the endpoint as authenticated
  requests.

## [0.6.0] - 2026-08-06

Spec: `specs/007-user-authentication/spec.md`

### Added

- Backend: self-hosted JWT authentication — `POST /v1/auth/register`,
  `/login`, `/logout`, `/refresh` — with no third-party identity provider.
  Passwords are hashed with bcrypt and never stored in a reversible form.
  Access tokens are short-lived (15 min default); refresh tokens are
  rotated on every use and stored hashed, delivered as an httpOnly,
  `SameSite=Lax` cookie.
- Backend: basic protection against rapid repeated failed login attempts
  against the same account.
- Backend: open, self-service registration — an email, password, and one
  of Sporting/Technical/Financial department, with no admin/invite step
  and no password complexity requirement beyond non-empty.
- Frontend: login and registration pages, a route guard gating the app's
  existing routes behind a logged-in session, and an HTTP interceptor
  attaching the access token to outgoing requests. The access token lives
  in memory only (never `localStorage`/`sessionStorage`); an
  `APP_INITIALIZER` performs a silent refresh before the app finishes
  bootstrapping, so a hard page reload doesn't race the auth guard.
- Frontend: the navbar shows the logged-in staff member's email and a
  working logout control.

### Changed

- Constitution (`.specify/memory/constitution.md`, 1.1.0 → 1.2.0):
  Principle V and the Technology & Security Constraints no longer
  reference AWS Cognito — authentication is declared self-hosted; added a
  requirement that password credentials be hashed with a modern adaptive
  algorithm and never stored in plaintext or reversibly encrypted.

## [0.5.0] - 2026-08-06

Spec: `specs/006-pdf-ingestion-pipeline/spec.md`

### Added

- Backend: a locally-invoked CLI
  (`python -m src.modules.ingestion.cli --file ... --title ... --department ...`)
  that ingests a PDF regulation document — extracting its text, splitting
  it into fixed-size overlapping chunks, embedding each chunk via AWS
  Bedrock Titan Text Embeddings V2, and writing one `documents` row plus
  one `document_chunks` row per chunk (feature 005's schema) inside a
  single transaction.
- Backend: re-ingesting a title that already exists is rejected before any
  parsing or embedding work happens; any failure partway through a run
  (bad file, bad department, an embedding-call error) leaves no partial
  document or chunk data behind.
- Backend: `src/core/` (`config.py`, `db.py`) — the first real use of the
  cross-cutting `core/` folder named in the constitution's Separation of
  Concerns amendment — providing typed `.env` config and a shared Postgres
  connection helper for this and future modules.

## [0.4.0] - 2026-08-05

Spec: `specs/004-chat-frontend-integration/spec.md`

### Added

- Frontend: the chat UI is now wired to the backend's `/v1/chat` address
  (feature 003) — sending a message calls the backend and renders its reply
  as its own bubble, visually distinct from the user's messages, updating
  incrementally as words arrive rather than appearing all at once.
- Frontend: a message's reply shows a clear failure indication if the
  backend is unreachable or the connection drops mid-stream (after a
  10-second silence), while preserving whatever partial reply already
  arrived and the user's own message.
- Frontend: sending a new message is blocked while a previous message's
  reply is still arriving, and re-enabled once it completes or fails.

### Changed

- Backend: CORS now allows `POST` in addition to `GET`, so the browser can
  actually reach `/v1/chat` (previously configured for the health check's
  `GET` only).
- Backend: the placeholder reply is now paced 150ms apart per word (was
  effectively instant), so the streaming behavior added in 0.3.0 is
  actually visible to a client watching it arrive.

## [0.3.0] - 2026-08-04

Spec: `specs/003-chat-api-sse/spec.md`

### Added

- Backend: `POST /v1/chat` — the app's primary chat address — accepting a
  message and streaming back a fixed placeholder reply ("Hello, this is a
  test response.") via Server-Sent Events, delivered as multiple discrete
  word-level events rather than a single blocking response.
- Backend: rejects requests with a missing, empty, or whitespace-only
  message rather than returning a reply for them.
- Backend: unauthenticated, consistent with the rest of the skeleton; each
  request is handled independently with no shared state across concurrent
  chats.

## [0.2.0] - 2026-08-04

Spec: `specs/002-chat-interface-ui/spec.md`

### Added

- Frontend: a chat interface — navbar, chatbox, and a multi-line textbox
  (Enter to send, Shift+Enter for a newline) — as the application's root
  page, with sent messages appended as chat bubbles.
- Frontend: client-side routing — `/` now serves the chat interface, and
  the health-status indicator (0.1.0) moved to its own `/health` address so
  it no longer shares the root page with chat.
- Frontend: Tailwind CSS for a responsive layout across mobile, tablet, and
  desktop widths.

## [0.1.0] - 2026-08-04

Spec: `specs/001-skeleton-health-check/spec.md`

### Added

- Backend: FastAPI application with an unauthenticated `GET /health`
  endpoint responding in under 500ms.
- Frontend: Angular application with a health-status indicator (healthy /
  unreachable / checking) on the root page, calling the backend's health
  check on load.
- Project constitution (`.specify/memory/constitution.md`) defining
  test-first development, unit testing, API contract consistency, clean
  code, and separation-of-concerns principles — including folder
  conventions (`core/`, `shared/`, `features/<name>/` for the frontend;
  `modules/<name>/`, `core/` for the backend).
- Test scripts: `scripts/test-backend.sh`, `scripts/test-frontend.sh`,
  `scripts/test.sh`.
- VS Code debugger configuration for the backend (FastAPI, pytest) and
  frontend (Chrome).
- App-wide version tracking (`VERSION`, `frontend/package.json`,
  `backend/src/__init__.py`).

### Changed

- Frontend test runner migrated from Karma/Jasmine to Vitest.
