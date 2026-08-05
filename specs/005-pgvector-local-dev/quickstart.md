# Quickstart: Local Vector Database for Regulation Chunks

Validates the local database end-to-end per the user stories in
[spec.md](./spec.md). Schema contract: [contracts/schema.md](./contracts/schema.md).
Data shape: [data-model.md](./data-model.md).

## Prerequisites

- Docker installed and running

## 1. Start the database directly (User Story 1)

```bash
cp .env.example .env   # only if you don't already have one
docker compose up -d
```

**Expected**: a `db` service starts, using the `pgvector/pgvector:0.8.1-pg16`
image, and becomes healthy within a few seconds.

## 2. Verify the schema (Acceptance Scenarios 1–2)

```bash
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dx" -c "\d documents" -c "\d document_chunks"
```

**Expected**: `\dx` lists the `vector` extension; `\d documents` shows `id`,
`title`, `created_at`; `\d document_chunks` shows `id`, `document_id`,
`chunk_text`, `embedding` (`vector(1024)`), `department`, `chunk_order`,
`created_at`, plus the foreign key and the `(document_id, chunk_order)`
unique constraint.

## 3. Verify data persists across a restart (Acceptance Scenario 3)

```bash
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "INSERT INTO documents (title) VALUES ('quickstart-check');"
docker compose restart db
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "SELECT title FROM documents WHERE title = 'quickstart-check';"
```

**Expected**: the row is still there after the restart. Clean up afterward:

```bash
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "DELETE FROM documents WHERE title = 'quickstart-check';"
```

## 4. Run the onboarding script end-to-end (User Story 2)

On a machine without an existing backend `.venv`, frontend `node_modules`,
or `.env`:

```bash
./scripts/dev-setup.sh
```

**Expected**: `backend/.venv` is created with dependencies installed,
`frontend/node_modules` is installed, the database container is running,
and `.env` exists (created from `.env.example`). Verify by starting both
apps per the root `README.md`.

## 5. Verify the onboarding script is safe to re-run (Acceptance Scenario 5)

```bash
./scripts/dev-setup.sh
```

**Expected**: completes again without error, and does not touch an already
-customized `.env` — confirm by editing a value in `.env` first, re-running,
and checking the edit is still there.

## 6. Run the automated integration test

```bash
cd backend
source .venv/bin/activate
pytest tests/integration
```

**Expected**: the schema-verification test passes, confirming the extension
and both tables match the contract — requires the database from step 1 to
already be running.
