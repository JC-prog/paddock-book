# Quickstart: Foundational Application Skeleton with Health Check

Validates the walking skeleton end-to-end per User Story 1 in [spec.md](./spec.md).
Contract: [contracts/health-api.yaml](./contracts/health-api.yaml). Data shape:
[data-model.md](./data-model.md).

## Prerequisites

- Python 3.12 and a virtual environment tool (`venv`, `uv`, or equivalent)
- Node.js (LTS) and the Angular CLI (`npm install -g @angular/cli`)

## 1. Run the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

**Expected**: server starts on `http://localhost:8000`.

Verify directly (Acceptance Scenario 1):

```bash
curl -i http://localhost:8000/health
```

**Expected**: `200 OK` with JSON body `{"status": "ok"}`, returned in well under 500ms
(SC-004).

## 2. Run the frontend

```bash
cd frontend
npm install
ng serve
```

**Expected**: dev server starts on `http://localhost:4200`.

## 3. Verify end-to-end (Acceptance Scenario 2)

Open `http://localhost:4200` in a browser.

**Expected**: the page shows a brief "checking" state, then a clear "backend healthy"
indication (FR-004, SC-003).

## 4. Verify the unreachable state (Acceptance Scenario 3)

Stop the backend process (Ctrl+C in its terminal), then reload
`http://localhost:4200`.

**Expected**: the page shows a clear "backend unreachable" indication — not a silent
failure or a generic browser error (FR-004, SC-002).

Restart the backend and reload again to confirm recovery.

## 5. Run the automated tests

```bash
# Backend unit tests
cd backend && pytest tests/unit

# Frontend unit tests
cd frontend && ng test --watch=false
```

**Expected**: all tests pass, including cases for healthy, unreachable, and in-progress
states (Constitution Principles I & II).
