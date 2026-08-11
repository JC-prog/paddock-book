# Implementation Plan: RAG Evaluation Harness

**Branch**: `014-rag-eval-harness` | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-rag-eval-harness/spec.md`

## Summary

Adds a two-command CLI, mirroring `modules/ingestion/cli.py`'s and
`modules/download/cli.py`'s shape, that lets an operator (1) synthesize a
fixed, reusable set of test questions from a department's currently-ingested
documents via an LLM, and (2) replay that fixed set through the real,
unmodified chat retrieval and generation pipeline, scoring each question's
retrieval correctness (was its source document retrieved) and answer
correctness (LLM-as-judge against the expected answer from step 1), and
writing a markdown report. Eval sets and reports are timestamped files under
`data/eval/`, never overwritten, so a naive-RAG baseline report today can be
compared by eye against a future reranking-run report over the identical
question set.

## Technical Context

**Language/Version**: Python 3.12 (backend — same as the rest of the repo)

**Primary Dependencies**: None new — `ollama` (already used by
`modules/chat/generation.py` and `core/embeddings.py`'s Ollama path),
`psycopg` (reading `documents`/`document_chunks`, already-existing tables)

**Storage**: Postgres, read-only — this feature adds no new tables and no
new columns. It reads the existing `documents`/`document_chunks` tables
(feature 001) to source real ingested content for question generation.
Eval sets and reports themselves are files under `data/eval/`, not
database records (spec.md Assumptions).

**Testing**: pytest — unit tests for question generation, judging, and
metric computation with the Ollama client mocked (matching
`tests/unit/test_chat_generation.py`'s existing `client_factory`
injection pattern); integration tests for the department-scoped
document/chunk read against real Postgres

**Target Platform**: Same backend as every other feature — this is an
operator-run CLI within it, not a new service

**Project Type**: CLI tool within the existing web-application backend
(matches `modules/ingestion/`, `modules/download/`, `modules/admin/`'s
existing CLI-entry-point pattern)

**Performance Goals**: None beyond existing bars — this is an
operator-triggered, offline batch tool, not a request-serving path

**Constraints**: MUST NOT alter `modules/chat/retrieval.py` or
`modules/chat/generation.py`'s existing behavior (FR-012) — the "run"
step calls their existing public functions unchanged, exactly as real
chat requests do, so a measured result is actually representative of
what a real user would experience; a failure generating or judging any
single question MUST NOT abort the rest of a run (FR-013)

**Scale/Scope**: Two CLI subcommands, no new database schema, no new
API surface, no frontend changes — deliberately not a general eval
framework (spec.md Assumptions: files not a DB, CLI not a UI)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Test-First Development**: Applies as normal — every new
  generation/judging/metrics/report function gets a failing test first
  in `tasks.md`. PASS.
- **II. Comprehensive Unit Testing**: The new `modules/eval/repository.py`
  (reading documents/chunks for a department) gets integration tests
  against real Postgres; question generation, judging, metric
  computation, and report writing are unit-tested with the Ollama
  client mocked, matching `modules/chat/generation.py`'s existing
  `client_factory` DI pattern — no unit test depends on live Ollama.
  PASS.
- **III. API Contract Consistency**: N/A — this feature exposes no
  HTTP API; its "contract" is the CLI's argument interface and the
  eval-set/report file formats, documented in `contracts/` per this
  project's established practice of contracts covering whatever
  interface a feature actually exposes (feature 009's CLI contract is
  the direct precedent). PASS.
- **IV. Clean Code & Readability**: Applies as normal. PASS.
- **V. Separation of Concerns**: A new, self-contained `modules/eval/`
  bounded domain (repository + service + schemas + cli). It calls
  `modules/chat/retrieval.py`'s and `modules/chat/generation.py`'s
  existing public functions directly, unmodified — a modules-to-modules
  dependency, which the constitution's layering rule permits (only
  `core/` importing from `modules/` is forbidden; feature 013's
  `modules/jobs/` → `modules/download/`+`modules/ingestion/` is the
  direct precedent for this same shape). PASS.

No Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/014-rag-eval-harness/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   └── modules/
│       └── eval/                 # NEW module
│           ├── __init__.py
│           ├── repository.py     # reads documents/document_chunks for a department (existing tables, read-only)
│           ├── schemas.py        # EvalQuestion, EvalSet, EvalReport (Pydantic, for JSON/markdown (de)serialization)
│           ├── question_gen.py   # LLM call: chunk text -> {question, expected_answer}
│           ├── judge.py          # LLM call: (expected_answer, generated_answer) -> correct/incorrect
│           ├── service.py        # generate_eval_set(), run_eval() — orchestrates the above + chat's retrieval/generation
│           └── cli.py            # `generate --department X [--questions-per-doc N]`, `run --eval-set <path>`
└── tests/
    ├── unit/
    │   ├── test_eval_question_gen.py   # NEW — Ollama client mocked
    │   ├── test_eval_judge.py          # NEW — Ollama client mocked
    │   └── test_eval_service.py        # NEW — repository/retrieval/generation/judge all mocked
    └── integration/
        └── test_eval_repository.py     # NEW — real Postgres

backend/data/eval/    # NEW — sets/ and reports/ subdirectories

.gitignore             # MODIFIED — fixes /data/ (never actually matched
                        # backend/data/, per research.md) to /backend/data/,
                        # covering both this feature's new directory and the
                        # pre-existing data/regulations/ gap
```

**Structure Decision**: A new, self-contained `modules/eval/` bounded
domain, matching every other module's shape, composing
`modules/chat/retrieval.py` and `modules/chat/generation.py`'s existing
public functions rather than duplicating them (FR-012). No API router —
this feature's only entry point is `cli.py`, consistent with
`modules/ingestion/`, `modules/download/`, and `modules/admin/`'s CLI
precedents.

## Complexity Tracking

*No violations — table intentionally omitted.*
