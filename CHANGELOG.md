# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
This file is maintained by hand — update it alongside each version bump in
`VERSION` (see `README.md`); no `/speckit-*` command updates it automatically.
Each entry below corresponds to the spec-kit feature of the same number
under `specs/`.

## [Unreleased]

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
