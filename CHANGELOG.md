# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
This file is maintained by hand — update it alongside each version bump in
`VERSION` (see `README.md`); no `/speckit-*` command updates it automatically.

## [Unreleased]

## [0.1.0] - 2026-08-04

### Added

- Backend: FastAPI application with an unauthenticated `GET /health` endpoint
  responding in under 500ms.
- Frontend: Angular application with a chat interface (navbar, chatbox with
  auto-scrolling message bubbles, and a multi-line textbox — Enter to send,
  Shift+Enter for a newline) as the root page.
- Frontend: client-side routing — `/` serves the chat interface, `/health`
  serves the backend health-status indicator, both lazy-loaded per feature.
- Frontend: Tailwind CSS for responsive layout across mobile, tablet, and
  desktop widths.
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
