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
Public repository. Contains references to internal financial reporting
processes — review any content before adding it here.

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

## Running Fully Locally (Ollama, no AWS)

The chat/ingestion pipeline defaults to AWS Bedrock for embeddings, but
runs entirely locally against [Ollama](https://ollama.com) instead —
useful for trying the RAG pipeline out before touching any AWS
infrastructure. In `backend/.env` (see `backend/.env.example`):

```bash
EMBEDDING_PROVIDER=ollama
```

Then pull both models Ollama needs (chat generation and embeddings are
separate models):

```bash
ollama pull llama3.2
ollama pull mxbai-embed-large
```

Ingested content and chat queries must use the same `EMBEDDING_PROVIDER`
— each produces vectors in a different embedding space, so don't switch
providers after you've already ingested documents with the other one.

## Getting Real Content Into the Knowledge Base

A fresh local setup starts with an empty knowledge base — chat has
nothing to answer from until you download and ingest some regulation
PDFs. The short version, once the backend/frontend above are running:

1. **Promote your account to admin**: register/log in once via the app,
   then `python -m src.modules.admin.cli --promote-admin you@example.com`
   from `backend/` (see `specs/012-admin-logging-panel/quickstart.md`).
2. **Download a category's PDFs**: either the CLI
   (`python -m src.modules.download.cli --category 110`, see
   `specs/009-fia-pdf-download/quickstart.md`) or, once the worker below
   is running, the admin panel's Jobs page.
3. **Ingest what you downloaded**: either the CLI
   (`python -m src.modules.ingestion.cli --file ... --title ... --department ...`,
   see `specs/006-pdf-ingestion-pipeline/quickstart.md`) or the same
   Jobs page's ingest form (`specs/013-download-ingest-jobs/quickstart.md`)
   — the admin panel's ingest job reads an entire downloaded category at
   once, so it's the faster path for real use.
4. **Chat**: ask a question in the department you ingested into.

The Jobs page (step 2/3 via the panel) needs Redis and a worker process
running too:

```bash
docker compose up -d          # now also starts redis alongside db
cd backend
celery -A src.worker worker --loglevel=info
```

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
