# Quickstart: Chat API with Streamed Responses

Validates the `/v1/chat` address end-to-end per the user story in
[spec.md](./spec.md). Contract: [contracts/chat-api.md](./contracts/chat-api.md).
Data shape: [data-model.md](./data-model.md). Backend-only — no frontend
changes are involved in this feature.

## Prerequisites

- Backend virtual environment set up per the root `README.md` (`backend/.venv`
  with `pip install -r requirements.txt`, including the new `sse-starlette`
  dependency added by this feature)

## 1. Run the backend

```bash
cd backend
source .venv/bin/activate
uvicorn src.main:app --reload --port 8000
```

**Expected**: server starts on `http://localhost:8000`.

## 2. Send a valid message and watch it stream (Acceptance Scenarios 1–3)

```bash
curl -N -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "hello there"}'
```

**Expected**: six `data: ...` lines print one at a time (not all at once) —
"Hello,", "this", "is", "a", "test", "response." — then the connection
closes. The `-N` flag disables curl's output buffering so the incremental
arrival is actually visible.

## 3. Send an empty message (Acceptance Scenario 4)

```bash
curl -i -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "   "}'
```

**Expected**: `422` response, no `data:` lines — the request is rejected
before any placeholder reply is produced.

## 4. Disconnect mid-stream (Acceptance Scenario 5)

```bash
curl -N -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "hello there"}' \
  --max-time 0.05
```

**Expected**: curl cuts the connection almost immediately; check the backend
process's logs/console — there should be no unhandled exception or traceback
printed as a result.

## 5. Run the automated tests

```bash
cd backend
source .venv/bin/activate
pytest tests/unit
```

**Expected**: all tests pass, including cases for multi-event delivery
(SC-005), empty-message rejection (SC-003), and completion detection
(SC-002, SC-004).
