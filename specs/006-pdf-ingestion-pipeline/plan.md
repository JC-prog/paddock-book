# Implementation Plan: PDF Regulation Ingestion Pipeline

**Branch**: `006-pdf-ingestion-pipeline` | **Date**: 2026-08-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-pdf-ingestion-pipeline/spec.md`

## Summary

A locally-invoked CLI that takes one PDF and a department, extracts its
text, splits it into fixed-size overlapping chunks, embeds each chunk via
AWS Bedrock Titan Text Embeddings V2, and writes a `documents` row plus one
`document_chunks` row per chunk (feature 005's schema) inside a single
database transaction — so a failed run leaves nothing behind. Re-ingesting a
title that already exists is rejected up front, before any parsing or
embedding work happens. This is the first backend code that actually
connects to Postgres or calls Bedrock, so it's also where `backend/src/core/`
(config, DB connection) is introduced for the first time.

## Technical Context

**Language/Version**: Python 3.12 (unchanged)

**Primary Dependencies**: `pypdf` 6.14.2 (PDF text extraction — permissive
BSD-3-Clause license, pure Python, no native build step); `boto3` 1.43.65
(AWS SDK, for the Bedrock Runtime `InvokeModel` call to
`amazon.titan-embed-text-v2:0`); `pydantic-settings` 2.14.2 (typed `.env`
config — first real use of `backend/src/core/`); `psycopg` (already a
dependency since feature 005) for the transactional write

**Storage**: PostgreSQL + pgvector (feature 005's `documents`/
`document_chunks` tables) — this feature is the first to actually write to
them

**Testing**: pytest. `parser`/`chunker` are pure-function unit tests;
`embeddings` is unit-tested against a mocked `boto3` client (no real AWS
call); `service` is unit-tested with all four collaborators mocked
(verifies orchestration/ordering, not real I/O); `repository` needs a real
Postgres and lives in `tests/integration/`, per the same Constitution
Principle II distinction feature 005 established

**Target Platform**: Local developer machines (same as feature 005) — this
feature runs against the local database, not a hosted one

**Project Type**: Backend-only, CLI addition — no new API endpoint, no
frontend changes

**Performance Goals**: Not specified as a hard number in spec.md — a
typical regulation PDF should ingest in well under a minute locally;
correctness (SC-002–SC-005) matters more than speed for a manually-invoked,
one-document-at-a-time tool

**Constraints**: All-or-nothing writes (FR-008); duplicate titles rejected
before any parsing/embedding work, to avoid burning Bedrock calls on a run
that's going to be rejected anyway (FR-007); embedding vector must match
the database's existing `vector(1024)` column (FR-004)

**Scale/Scope**: One new backend module (`modules/ingestion/`), two new
`core/` files (`config.py`, `db.py`), no schema changes (feature 005's
schema is used as-is)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature | Status |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Yes — failing tests for `parser`, `chunker`, `embeddings` (mocked), `repository` (integration), and `service` (orchestration, mocked collaborators) must exist before their implementations | PASS (enforced at task-generation/implementation time) |
| II. Comprehensive Unit Testing | Yes — `parser`/`chunker`/`embeddings`/`service` are true unit tests with no live dependency (Bedrock is mocked); `repository` correctly lives in `tests/integration/` since it needs a real Postgres, matching feature 005's established distinction | PASS |
| III. API Contract Consistency | N/A — no API endpoint is added; the only "contract" is the CLI's arguments and the database write shape, both documented in `contracts/` | PASS (N/A) |
| IV. Clean Code & Readability | Yes — `parser`/`chunker`/`embeddings`/`repository` are each single-purpose and independently testable; no NLP/tokenizer dependency added just to approximate a word-count chunk size; no migration framework introduced | PASS |
| V. Separation of Concerns | Yes — `modules/ingestion/` mirrors the existing `modules/health/`+`modules/chat/` convention (with `cli.py` standing in for `router.py`, since there's no HTTP surface); `config.py`/`db.py` go in `core/` since retrieval (the next feature) will reuse them rather than duplicating connection logic | PASS |

No violations. Complexity Tracking is not needed.

**Post-Phase 1 re-check**: research.md, data-model.md, contracts/cli.md, and
quickstart.md introduce no new dependency, module, or pattern beyond what
Technical Context and the table above already accounted for — `core/`
gains exactly the two files anticipated, `modules/ingestion/` mirrors the
existing router/service/schemas/repository shape with `cli.py` standing in
for `router.py`, and the transactional all-or-nothing write (FR-008)
requires no exception to Principle IV or V. All 5 principles remain PASS.

## Project Structure

### Documentation (this feature)

```text
specs/006-pdf-ingestion-pipeline/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── requirements.txt              # modified — add pypdf, boto3, pydantic-settings
└── src/
    ├── core/
    │   ├── __init__.py            # new
    │   ├── config.py               # new — Settings (pydantic-settings), reads .env
    │   └── db.py                    # new — shared psycopg connection helper
    └── modules/
        └── ingestion/
            ├── __init__.py
            ├── cli.py                # new — entry point: python -m src.modules.ingestion.cli
            ├── parser.py              # new — PDF → raw text
            ├── chunker.py             # new — raw text → overlapping fixed-size chunks
            ├── embeddings.py           # new — Bedrock Titan V2 call: text → vector
            ├── repository.py           # new — transactional write to documents/document_chunks
            └── service.py               # new — orchestrates: duplicate-check → parse →
                                          #        chunk → embed all → write all-or-nothing

backend/tests/
├── unit/
│   ├── test_ingestion_parser.py       # new
│   ├── test_ingestion_chunker.py      # new
│   ├── test_ingestion_embeddings.py   # new (mocked boto3)
│   └── test_ingestion_service.py      # new (mocked collaborators)
└── integration/
    └── test_ingestion_repository.py    # new — real Postgres required

frontend/                                # untouched by this feature
```

**Structure Decision**: Follows the existing `modules/<name>/` convention
(router/service/schemas/repository per Constitution Principle V), adapted
for a CLI instead of an HTTP surface — `cli.py` plays the role `router.py`
plays elsewhere. `config.py` and `db.py` land in `core/` rather than inside
`modules/ingestion/` specifically so the next feature (retrieval) can reuse
them instead of re-deriving its own DB connection — this is the first real
use of `core/`, matching how the constitution named "config" and "db
session" as its canonical examples back when it was amended. Tests split
`unit/` vs `integration/` exactly the way feature 005 established: anything
touching a live dependency (Bedrock or Postgres) is an integration test or
is mocked; nothing "unit" silently depends on either.

## Complexity Tracking

*Not applicable — the Constitution Check above has no violations to justify.*
