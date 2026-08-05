---

description: "Task list for Local Vector Database for Regulation Chunks"
---

# Tasks: Local Vector Database for Regulation Chunks

**Input**: Design documents from `/specs/005-pgvector-local-dev/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/schema.md, quickstart.md

**Tests**: The schema itself is tested (Constitution Principle I applies) via a new integration test — see research.md/plan.md for why it's an integration test, not a unit test. The onboarding script (User Story 2) is validated manually via quickstart.md instead of an automated test, since asserting a bash script's OS/filesystem side effects (venv creation, npm install, Docker startup) doesn't fit pytest the way schema shape does — matching how feature 002 handled pure-CSS work that unit tests couldn't meaningfully assert.

**Organization**: Tasks are grouped by user story from spec.md (US1 = P1, US2 = P2).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Paths below are repo-root-relative except where noted under `backend/`

---

## Phase 1: Setup

**Purpose**: Add the new test dependency and scaffold the integration test directory

- [ ] T001 [P] Add `psycopg[binary]` to `backend/requirements.txt`
- [ ] T002 [P] Create the `backend/tests/integration/` package (`__init__.py`), separate from `tests/unit/` per Constitution Principle II

**Checkpoint**: The integration test directory exists and the Postgres driver is installable.

---

## Phase 2: User Story 1 - Provision a local database that mirrors production storage (Priority: P1) 🎯 MVP

**Goal**: A single command starts a local Postgres + pgvector database with the `documents`/`document_chunks` schema already provisioned, persisting data across restarts, with every backend connection setting documented (spec.md User Story 1).

**Independent Test**: Start the local database and confirm the schema exists with the expected columns and the vector extension enabled — fully verifiable with no application code.

### Test for User Story 1 ⚠️

> **NOTE: Write this test FIRST, ensure it FAILS before implementation (Constitution Principle I)**

- [ ] T003 [US1] Write a failing integration test in `backend/tests/integration/test_schema.py` verifying: the `vector` extension is enabled; `documents` has `id`, `title`, `created_at`; `document_chunks` has `id`, `document_id` (FK to `documents`), `chunk_text`, `embedding` (`vector(1024)`), `department` (enum: sporting/technical/financial), `chunk_order`, `created_at`; and the `(document_id, chunk_order)` unique constraint exists — per `data-model.md` and `contracts/schema.md`

### Implementation for User Story 1

- [ ] T004 [P] [US1] Write `db/init/001_init_schema.sql` — `CREATE EXTENSION IF NOT EXISTS vector`, the `department` enum type, and the `documents`/`document_chunks` tables with their FK and unique constraint, per `data-model.md`
- [ ] T005 [P] [US1] Write `docker-compose.yml` — a `db` service using `pgvector/pgvector:0.8.1-pg16` (research.md), a named volume for persistence (FR-002), a healthcheck, and `db/init/` mounted read-only into `/docker-entrypoint-initdb.d/`
- [ ] T006 [P] [US1] Write `.env.example` at the repo root — `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`, `POSTGRES_HOST`, and a combined `DATABASE_URL`, all safe non-secret local-dev placeholder values (FR-005)
- [ ] T007 [US1] Start the database (`docker compose up -d`) and run the integration test against it, confirming it passes (depends on T003, T004, T005, T006) — makes T003 pass
- [ ] T008 [US1] Manually validate Acceptance Scenarios 1–4 (extension/schema shape, persistence across a restart, `.env.example` completeness) via quickstart.md steps 1–3 (depends on T007)

**Checkpoint**: At this point, User Story 1 is fully functional and independently testable — this is the MVP.

---

## Phase 3: User Story 2 - Bootstrap a new developer's entire local environment in one step (Priority: P2)

**Goal**: A single script sets up a new developer's backend virtual environment, frontend dependencies, local database, and `.env` file — safe to re-run without destroying existing work (spec.md User Story 2).

**Independent Test**: On a machine with only the prerequisites installed, run the onboarding script from a fresh clone and confirm it finishes with a working backend environment, installed frontend dependencies, a running database, and a populated `.env`.

- [ ] T009 [US2] Write `scripts/dev-setup.sh`: check Docker is installed/running with a clear, actionable error if not (Edge Case); create `backend/.venv` and install dependencies if missing; run `npm install` in `frontend/`; run `docker compose up -d`; copy `.env.example` to `.env` only if `.env` does not already exist (FR-006–FR-008) (depends on T005, T006 existing to orchestrate)
- [ ] T010 [US2] Manually validate Acceptance Scenarios 1–5 (fresh-clone bootstrap, and a safe idempotent re-run that leaves a customized `.env` untouched) via quickstart.md steps 4–5 (depends on T009)

**Checkpoint**: Both user stories are independently functional — the database can be started directly (US1), or a new developer can bootstrap everything at once (US2).

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Final validation

- [ ] T011 Run full quickstart.md validation (the integration test, plus all manual scenarios from steps 1–5) and confirm SC-001–SC-005 are met (depends on T008, T010)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **User Story 1 (Phase 2)**: Depends on Setup completion (needs the integration test package and `psycopg` installable)
- **User Story 2 (Phase 3)**: Depends on User Story 1's `docker-compose.yml` and `.env.example` existing (T005, T006) — the onboarding script orchestrates them rather than duplicating them, so it is not independent of US1 the way most story pairs are
- **Polish (Phase 4)**: Depends on both user stories being complete

### Within User Story 1

- Test (T003) MUST be written and FAIL before implementation (Constitution Principle I)
- `db/init/001_init_schema.sql`, `docker-compose.yml`, and `.env.example` (T004–T006) are independent of each other — different files, no shared dependency
- All three (T004–T006) before starting the database and running the test against it (T007)
- Implementation complete (T007) before manual scenario validation (T008)

### Parallel Opportunities

- T001 and T002 (Setup) can run in parallel — different files
- T004, T005, and T006 (US1 implementation) can run in parallel — three independent files

---

## Parallel Example: User Story 1

```bash
# Once T003 (test) exists and fails, these three can proceed together:
Task: "Write db/init/001_init_schema.sql"
Task: "Write docker-compose.yml"
Task: "Write .env.example"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: User Story 1
3. **STOP and VALIDATE**: Run quickstart.md steps 1–3 (T008)
4. The database is usable on its own at this point — User Story 2 is a convenience layered on top, not a blocker for anything else depending on the schema existing

### Incremental Delivery

1. Complete Setup + User Story 1 → database provisioned and verified (MVP!)
2. Add User Story 2 → one-command onboarding → validate
3. Complete Polish → full quickstart.md validation

---

## Notes

- [P] tasks = different files, no dependencies
- [US1]/[US2] labels map every task to its spec.md story for traceability
- Verify the test fails before implementing (Constitution Principle I is NON-NEGOTIABLE for this project)
- Commit after each task or logical group, split by conventional-commit type (`feat:`, `test:`, `chore:`) rather than one combined commit
- PDF parsing, chunk-splitting logic, the embedding-generation call, and any ingestion pipeline are explicitly out of scope for this feature (see spec.md Assumptions) — do not add them here
- No ANN similarity-search index (HNSW/IVFFlat) is added in this feature (research.md) — do not add one here
