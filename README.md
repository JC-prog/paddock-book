# PaddockBook

Internal RAG knowledge assistant for F1 team staff. Answers questions
against Sporting, Technical, and Financial regulation documents with 
department-aware retrieval.

**Status**: early development

## Stack
FastAPI, Postgres + pgvector, AWS (Lambda/Fargate, Cognito, CDK), Angular,
Anthropic API/Bedrock

## Access
Private repository. Contains references to internal financial reporting
processes — do not make public without review.

## Local Development

See [specs/001-skeleton-health-check/quickstart.md](specs/001-skeleton-health-check/quickstart.md)
for full setup steps. Quick reference:

```bash
# Backend (FastAPI)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000

# Frontend (Angular), in a second terminal
cd frontend
npm install
npx ng serve --port 4200
```

Open `http://localhost:4200` — the page shows the backend's health status.

## Running Tests

```bash
./scripts/test-backend.sh    # pytest
./scripts/test-frontend.sh   # Vitest
./scripts/test.sh            # both, in sequence
```

Each script is independent, so backend and frontend contributors only need to
run the suite for the side they're touching. Requires the backend `.venv` and
frontend `node_modules` to already be set up (see Local Development above).
