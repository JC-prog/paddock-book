---

description: "Task list for PDF Regulation Ingestion Pipeline"
---

# Tasks: PDF Regulation Ingestion Pipeline

**Input**: Design documents from `/specs/006-pdf-ingestion-pipeline/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: Constitution Principle I (Test-First, NON-NEGOTIABLE) applies. `parser`/`chunker`/`embeddings`/`service` are true unit tests with no live dependency (Bedrock is mocked); `repository` needs a real Postgres and lives in `tests/integration/`, per the same Principle II distinction feature 005 established. `core/db.py` is a thin `psycopg` connection wrapper with no dedicated unit test of its own — it's exercised transitively by the `repository` integration test (T010/T014), matching how feature 005 left `docker-compose.yml` untested directly in favor of the integration test that runs against it.

**Organization**: This feature has a single user story (US1 = P1, spec.md) — the whole feature is the MVP; there is no incremental multi-story delivery here.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Paths below are `backend/`-relative except where stated in full

---

## Phase 1: Setup

**Purpose**: Add the new dependencies and scaffold the module/package structure

- [X] T001 [P] Add `pypdf==6.14.2`, `boto3==1.43.65`, `pydantic-settings==2.14.2` to `backend/requirements.txt` (research.md)
- [X] T002 [P] Create `backend/src/core/__init__.py` and `backend/src/modules/ingestion/__init__.py` (plan.md Project Structure) — `backend/tests/unit/` and `backend/tests/integration/` already exist from feature 005

**Checkpoint**: Dependencies installable, package skeleton exists.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `core/config.py` and `core/db.py` are the first real use of `backend/src/core/` (plan.md) — every ingestion module needs `DATABASE_URL`/AWS config or a DB connection, so this must land before any User Story 1 implementation.

**⚠️ CRITICAL**: No User Story 1 implementation task may start until this phase is complete.

- [X] T003 [P] Write a failing unit test in `backend/tests/unit/test_config.py` — `Settings` (pydantic-settings) requires `DATABASE_URL`, defaults/reads `AWS_REGION`, raises a clear validation error when `DATABASE_URL` is missing — confirmed failing before `config.py` exists (Constitution Principle I)
- [X] T004 Implement `backend/src/core/config.py` — `Settings` class (pydantic-settings) reading `.env`, per research.md's `pydantic-settings` decision — makes T003 pass (depends on T003)
- [X] T005 [P] Implement `backend/src/core/db.py` — shared `psycopg` connection helper built from `Settings.DATABASE_URL` (depends on T004)

**Checkpoint**: `core/config.py` and `core/db.py` exist — the ingestion module can now be built on top of them.

---

## Phase 3: User Story 1 - Ingest a regulation PDF into the searchable knowledge base (Priority: P1) 🎯 MVP

**Goal**: A developer runs one CLI command against a PDF and a department; the pipeline extracts text, splits it into overlapping fixed-size chunks, embeds each chunk via Bedrock Titan V2, and writes one `documents` row plus N `document_chunks` rows in a single transaction — or, on any failure (bad input, duplicate title, embedding error), writes nothing (spec.md).

**Independent Test**: Run the CLI against a sample PDF with a department specified, then inspect the database directly and confirm a new `documents` row exists along with multiple `document_chunks` rows linked to it, each carrying a non-empty embedding — fully verifiable with no retrieval code needed (spec.md).

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (Constitution Principle I)**

- [X] T006 [P] [US1] Write failing unit tests in `backend/tests/unit/test_ingestion_parser.py` — a valid PDF yields extracted text; a missing file, a corrupted file, and a PDF with no extractable text (e.g. scanned image) each raise a clear error (FR-002, Edge Cases)
- [X] T007 [P] [US1] Write failing unit tests in `backend/tests/unit/test_ingestion_chunker.py` — fixed-size ~500-word chunks with ~75-word overlap, `chunk_order` sequential starting at 0, the concatenated chunks (minus overlap) account for the full input text (FR-003, research.md, data-model.md's `Chunk`)
- [X] T008 [P] [US1] Write failing unit tests in `backend/tests/unit/test_ingestion_embeddings.py` — mocked `boto3` `bedrock-runtime` client; asserts the call targets `amazon.titan-embed-text-v2:0` with `dimensions: 1024`; returns a 1024-length vector on success; propagates a clear error when the mocked call fails (FR-004, data-model.md's `EmbeddedChunk`)
- [X] T009 [P] [US1] Write failing unit tests in `backend/tests/unit/test_ingestion_service.py` — `parser`/`chunker`/`embeddings`/`repository` all mocked; verifies orchestration order (department validated first, before any file/DB access → duplicate-title check → parse → chunk → embed all → write all-or-nothing, research.md); verifies an unsupported department rejects before `repository.title_exists()` or `parser.extract_text()` are ever called (Scenario 5); verifies an existing title rejects before `parser.extract_text()` is called (research.md's cost-avoidance rationale); verifies a bad file path (surfaced by a mocked `parser.extract_text()` raising) rejects before any write; verifies a mocked embedding failure results in zero repository writes (FR-008)
- [X] T010 [US1] Write a failing integration test in `backend/tests/integration/test_ingestion_repository.py` — requires the local database running (feature 005); verifies `title_exists()` correctly detects an existing title; verifies a successful write produces one `documents` row and N `document_chunks` rows with correct `chunk_order`/`department`/`embedding`; verifies a simulated failure partway through a write leaves zero rows in both tables (FR-008, contracts/cli.md) — confirmed failing (module doesn't exist) before implementation

### Implementation for User Story 1

- [X] T011 [P] [US1] Implement `backend/src/modules/ingestion/parser.py` — `pypdf`-based text extraction; raises a clear error for a missing/unreadable/corrupted file or a PDF with no extractable text — makes T006 pass
- [X] T012 [P] [US1] Implement `backend/src/modules/ingestion/chunker.py` — sliding-window fixed-size word-count chunking with overlap, per research.md's ~500-word/~75-word-overlap defaults — makes T007 pass
- [X] T013 [P] [US1] Implement `backend/src/modules/ingestion/embeddings.py` — `boto3` `bedrock-runtime` `InvokeModel` call to `amazon.titan-embed-text-v2:0` with `dimensions: 1024` — makes T008 pass
- [X] T014 [US1] Implement `backend/src/modules/ingestion/repository.py` — `title_exists()` query and a `write_document()` that writes one `documents` row plus all `document_chunks` rows inside a single `psycopg` transaction, using `core/db.py` — makes T010 pass (depends on T005, T010)
- [X] T015 [US1] Implement `backend/src/modules/ingestion/service.py` — orchestrates: validate department in-memory first, before any file read (FR-006, Scenario 5) → duplicate-title check via `repository.title_exists()` (FR-007) → `parser.extract_text()` (file existence/readability and corrupt/no-text-PDF errors surface here, still before any write — FR-006 Scenario 4) → `chunker` → embed every chunk via `embeddings` → `repository.write_document()` all-or-nothing (FR-008) — this ordering follows research.md's rationale precisely: the duplicate check comes before parsing too, not just before embedding, since research.md explicitly calls out avoiding wasted parsing time on a run that's going to be rejected anyway — makes T009 pass (depends on T009, T011, T012, T013, T014)
- [X] T016 [US1] Implement `backend/src/modules/ingestion/cli.py` — `argparse` entry point (`--file`, `--title`, `--department`), invokes `service`, maps outcomes to exit codes per contracts/cli.md (depends on T015)
- [X] T017 [US1] Manually validate Acceptance Scenarios 1–5 and the FR-007 re-ingestion rejection against a real sample PDF and the local database, via quickstart.md steps 1–4 (depends on T016) — **partial**: Scenarios 4–5 (missing file, bad department) and FR-008 (embedding-failure leaves zero rows) verified live against the real database with a real generated PDF; Scenarios 1–3 (successful ingestion) and FR-007 (duplicate rejection) require a real AWS Bedrock call, which no AWS credentials were available to make in this environment — those two are covered only by the mocked unit/integration suite (T009, T010), not a live run. Deferred as a manual follow-up once credentials are available (user decision, see conversation).

**Checkpoint**: User Story 1 is fully functional and independently testable — this is the MVP, and the entire feature.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Final validation

- [X] T018 Run full quickstart.md validation (unit suite, integration suite, and quickstart step 6) and confirm SC-001–SC-005 are met, including cleanup per the corrected Step 5 (`document_chunks` deleted before `documents` — no `ON DELETE CASCADE` exists) (depends on T017) — 41/41 automated tests passing (unit + integration, no regressions to feature 001–005's existing 15). SC-002 and SC-005 are confirmed via the mocked/integration suite rather than a live Bedrock run, per T017's note above.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all of User Story 1
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion (needs `core/config.py`/`core/db.py`)
- **Polish (Phase 4)**: Depends on User Story 1 being complete

### Within User Story 1

- Tests (T006–T010) MUST be written and FAIL before their corresponding implementation (Constitution Principle I)
- `parser`, `chunker`, `embeddings` (T011–T013) are independent of each other and of `repository` — different files, no shared dependency
- `repository` (T014) depends on `core/db.py` (T005) and its own test (T010)
- `service` (T015) depends on all four collaborators existing (T011–T014) and its own test (T009)
- `cli` (T016) depends on `service` (T015)
- Manual validation (T017) depends on `cli` (T016)

### Parallel Opportunities

- T001 and T002 (Setup) can run in parallel — different files
- T003 (Foundational test) has no parallel sibling — the only Foundational test
- T006, T007, T008, T009 (US1 unit tests) can run in parallel — four independent files; T010 (integration test) can be written alongside them
- T011, T012, T013 (US1 implementation) can run in parallel once their tests exist — three independent files

---

## Parallel Example: User Story 1

```bash
# Once T006-T010 (tests) exist and fail, these three can proceed together:
Task: "Implement backend/src/modules/ingestion/parser.py"
Task: "Implement backend/src/modules/ingestion/chunker.py"
Task: "Implement backend/src/modules/ingestion/embeddings.py"
```

---

## Implementation Strategy

### MVP First (and only) — User Story 1

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks User Story 1)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run quickstart.md steps 1–4 (T017)
5. Complete Phase 4: Polish — full quickstart.md validation (T018)

### Incremental Delivery

Not applicable — a single user story is the entire feature. Delivery is: Setup + Foundational → User Story 1 → Polish, in one pass.

---

## Notes

- [P] tasks = different files, no dependencies
- [US1] label maps every Phase 3 task to spec.md's single story for traceability
- Verify each test fails before implementing (Constitution Principle I is NON-NEGOTIABLE for this project)
- Commit after each task or logical group, split by conventional-commit type (`feat:`, `test:`, `chore:`) rather than one combined commit
- Retrieval, chat/generation wiring, automatic document discovery, and scheduled/triggered runs are explicitly out of scope (spec.md Assumptions) — do not add them here
- No update path for `document_chunks` — re-ingestion of an existing title is rejected, not merged (FR-007, data-model.md) — do not add an update/upsert path here
