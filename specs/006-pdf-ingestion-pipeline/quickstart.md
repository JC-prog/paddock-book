# Quickstart: PDF Regulation Ingestion Pipeline

Validates the pipeline end-to-end per the user story in
[spec.md](./spec.md). CLI contract: [contracts/cli.md](./contracts/cli.md).
Data shapes: [data-model.md](./data-model.md).

## Prerequisites

- The local database running (feature 005: `docker compose up -d`)
- `backend/.venv` set up with this feature's new dependencies installed
- AWS credentials configured (for the real Bedrock call) — any mechanism
  `boto3` resolves normally (env vars, shared config, IAM role)
- A sample PDF to ingest

## 1. Install the new dependencies

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Ingest a document (Acceptance Scenarios 1–3)

```bash
python -m src.modules.ingestion.cli \
  --file /path/to/sample-regulation.pdf \
  --title "Quickstart Test Document" \
  --department sporting
```

**Expected**: exits `0`. Verify directly:

```bash
docker compose exec -T db psql -U paddockbook -d paddockbook -c \
  "SELECT id, title FROM documents WHERE title = 'Quickstart Test Document';"
docker compose exec -T db psql -U paddockbook -d paddockbook -c \
  "SELECT chunk_order, department, length(chunk_text) FROM document_chunks
   WHERE document_id = (SELECT id FROM documents WHERE title = 'Quickstart Test Document')
   ORDER BY chunk_order;"
```

**Expected**: one `documents` row; multiple `document_chunks` rows with
`chunk_order` starting at 0 and increasing sequentially, all tagged
`department = sporting`.

## 3. Verify invalid input is rejected cleanly (Acceptance Scenarios 4–5)

```bash
# Bad file path
python -m src.modules.ingestion.cli --file /does/not/exist.pdf --title "X" --department sporting
echo "exit code: $?"

# Bad department
python -m src.modules.ingestion.cli --file /path/to/sample-regulation.pdf --title "Y" --department engine
echo "exit code: $?"
```

**Expected**: both exit non-zero with a clear error; confirm neither wrote
anything:

```bash
docker compose exec -T db psql -U paddockbook -d paddockbook -c \
  "SELECT title FROM documents WHERE title IN ('X', 'Y');"
```

**Expected**: no rows.

## 4. Verify re-ingesting an existing title is rejected (FR-007)

```bash
python -m src.modules.ingestion.cli \
  --file /path/to/sample-regulation.pdf \
  --title "Quickstart Test Document" \
  --department sporting
echo "exit code: $?"
```

**Expected**: non-zero exit, clear "already exists" error, no duplicate
`documents` row created.

## 5. Clean up the quickstart data

Feature 005's schema has no `ON DELETE CASCADE`, so `document_chunks` rows
must be removed before their parent `documents` row — this is also the
manual removal step FR-007 refers to when re-ingesting an existing title:

```bash
docker compose exec -T db psql -U paddockbook -d paddockbook -c \
  "DELETE FROM document_chunks WHERE document_id = (SELECT id FROM documents WHERE title = 'Quickstart Test Document');"
docker compose exec -T db psql -U paddockbook -d paddockbook -c \
  "DELETE FROM documents WHERE title = 'Quickstart Test Document';"
```

## 6. Run the automated tests

```bash
# Unit tests (parser, chunker, embeddings, service — no live dependencies)
cd backend && source .venv/bin/activate && pytest tests/unit

# Integration test (repository — requires the local database running)
./scripts/test-backend-integration.sh
```

**Expected**: all pass, including the all-or-nothing write test (simulating
a failure partway through and confirming zero rows are left behind).
