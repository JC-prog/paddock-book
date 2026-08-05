# Implementation Plan: Local Vector Database for Regulation Chunks

**Branch**: `005-pgvector-local-dev` | **Date**: 2026-08-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-pgvector-local-dev/spec.md`

## Summary

Provision a local Postgres + pgvector database (via Docker Compose, pinned to
pgvector 0.8.1 on PostgreSQL 16 to match Aurora PostgreSQL's current support)
with a `documents` / `document_chunks` schema sized for AWS Bedrock Titan
Text Embeddings V2's 1024-dimensional output, plus a root `.env.example` and
a `scripts/dev-setup.sh` onboarding script that bootstraps a new developer's
whole local environment in one run. No application code changes beyond a new
integration test proving the schema is correct — no PDF parsing, chunking,
embedding calls, or ingestion pipeline, per spec.md Assumptions.

## Technical Context

**Language/Version**: SQL (PostgreSQL 16 dialect) for the schema; Python 3.12
for the new integration test; Bash for the onboarding script — no changes to
the FastAPI application itself

**Primary Dependencies**: `pgvector/pgvector:0.8.1-pg16` Docker image
(matches Aurora PostgreSQL's current pgvector support — verified via AWS's
Aurora PostgreSQL release notes, which pgvector 0.8.1 across PostgreSQL
16.13/17.9/18.3); `psycopg[binary]` (new backend dependency, needed only to
write the schema-verification integration test — no FastAPI runtime code
connects to the database in this feature)

**Storage**: PostgreSQL 16 + pgvector 0.8.1, run locally via Docker Compose;
two tables (`documents`, `document_chunks`), no rows created by this feature

**Testing**: pytest, in a new `backend/tests/integration/` directory —
kept separate from `tests/unit/` per Constitution Principle II, which
explicitly requires tests touching a live database to be labeled and
isolated as integration tests, not counted as unit coverage

**Target Platform**: Local developer machines with Docker installed
(macOS/Linux/Windows via Docker Desktop) — same audience as the existing
`scripts/test.sh`/`README.md` setup instructions

**Project Type**: Infra/tooling — root-level Docker Compose config plus a
new backend integration test; no frontend changes, no new API endpoints

**Performance Goals**: A developer can go from a fresh clone to a running,
schema-provisioned database in under 5 minutes via one command (SC-001)

**Constraints**: pgvector pinned to 0.8.1 for Aurora consistency (FR-009);
embedding column sized for 1024 dimensions (FR-003); onboarding script MUST
NOT overwrite an existing `.env` and MUST be safe to re-run (FR-007, FR-008)

**Scale/Scope**: Two new tables, one new Docker Compose service, one new
onboarding script, one new integration test, one new Python dependency — no
existing code paths change

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature | Status |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Yes — the schema-verification integration test is written first (and fails, since neither the container nor the schema exist yet), then the Docker Compose config and SQL init script are added to make it pass | PASS (enforced at task-generation/implementation time) |
| II. Comprehensive Unit Testing | Yes, with a documented nuance — the only test this feature adds touches a live Postgres by nature (verifying a real schema), so it is a Constitution-defined integration test and lives in `tests/integration/`, not `tests/unit/`, and is not counted as unit coverage | PASS |
| III. API Contract Consistency | N/A in the literal sense (no API endpoint), but the schema itself is the contract future features (ingestion, retrieval) will code against — documented explicitly in `contracts/schema.md` so any future change updates the contract doc and the integration test together | PASS |
| IV. Clean Code & Readability | Yes — no migration framework introduced (none exists yet, per spec Assumptions), no speculative vector index added before there's real data or query patterns to justify one, onboarding script does only what FR-006–FR-008 require | PASS |
| V. Separation of Concerns | Yes — schema/init SQL lives under `db/init/`, separate from `backend/src/modules/` application code; the onboarding script is a standalone `scripts/` entry, not mixed into application code | PASS |

No violations. Complexity Tracking is not needed.

**Post-Phase 1 re-check**: `data-model.md` (two tables, one FK, one unique
constraint, one enum), `contracts/schema.md` (guarantees + explicit non-
guarantees), and `quickstart.md` introduce nothing beyond what Phase 0
research already accounted for. All five principles still PASS; no new
complexity, dependency beyond `psycopg[binary]`, or scope was added during
design.

## Project Structure

### Documentation (this feature)

```text
specs/005-pgvector-local-dev/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
docker-compose.yml              # new — pgvector/pgvector:0.8.1-pg16 service
.env.example                     # new — connection settings (root-level, so
                                  # Docker Compose auto-loads a sibling .env)

db/
└── init/
    └── 001_init_schema.sql       # new — vector extension, department enum,
                                   # documents + document_chunks tables

scripts/
├── dev-setup.sh                  # new — onboarding script (FR-006–FR-008)
├── test-backend.sh               # existing, unchanged
├── test-frontend.sh              # existing, unchanged
└── test.sh                       # existing, unchanged

backend/
├── requirements.txt              # modified — add psycopg[binary]
└── tests/
    └── integration/               # new — separate from tests/unit/
        ├── __init__.py
        └── test_schema.py         # new — verifies extension + table shape
```

**Structure Decision**: `docker-compose.yml` and `.env.example` sit at the
repository root (Docker Compose auto-loads a root-level `.env`, and the file
covers settings both the compose file and the backend need — it isn't
backend-specific). `db/init/` is a new top-level directory rather than
living under `backend/`, since the schema is a data-layer concern the
backend depends on rather than backend application source; the official
Postgres image auto-runs any `.sql` files mounted into
`/docker-entrypoint-initdb.d/` on first container startup, which is what
`001_init_schema.sql` is for. The new integration test lives in its own
`backend/tests/integration/` directory, never mixed with `tests/unit/`, per
Constitution Principle II's explicit distinction. No frontend changes and no
new FastAPI routes/modules — nothing in `backend/src/` changes.

## Complexity Tracking

*Not applicable — the Constitution Check above has no violations to justify.*
