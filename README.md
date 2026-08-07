# PaddockBook

Internal RAG knowledge assistant for F1 team staff. Answers questions
against Sporting, Technical, and Financial regulation documents with 
department-aware retrieval.

**Status**: early development

## Stack
FastAPI, Postgres + pgvector, AWS (Lambda/Fargate, CDK), Angular,
Anthropic API/Bedrock. Authentication is self-hosted (no third-party
identity provider).

## Access
Private repository. Contains references to internal financial reporting
processes — do not make public without review.

## Local Development

Run the onboarding script once (or whenever your environment needs
refreshing) to provision the backend `.venv`, frontend `node_modules`, and
the local Postgres + pgvector container:

```bash
./scripts/dev-setup.sh
```

Then, in two terminals:

```bash
# Backend (FastAPI)
cd backend
source .venv/bin/activate
uvicorn src.main:app --reload --port 8000

# Frontend (Angular)
cd frontend
npx ng serve --port 4200
```

Open `http://localhost:4200` — the page shows the backend's health status.
See individual feature quickstarts under `specs/*/quickstart.md` for
feature-specific setup (e.g. seeding data, applying new migrations).

## Running Tests

```bash
./scripts/test-backend.sh              # pytest, unit
./scripts/test-backend-integration.sh  # pytest, integration (requires local DB: docker compose up -d)
./scripts/test-frontend.sh             # Vitest
./scripts/test.sh                      # unit suites, in sequence
```

Each script is independent, so contributors only need to run the suite for
the side they're touching. Requires `./scripts/dev-setup.sh` to have been
run first (see Local Development above).
