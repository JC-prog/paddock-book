---

description: "Task list for feature implementation"
---

# Tasks: RAG Evaluation Harness

**Input**: Design documents from `/specs/014-rag-eval-harness/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required (not optional) — Constitution Principle I (Test-First
Development) is NON-NEGOTIABLE for this project: every implementation task
below has a corresponding test task that MUST be written first, confirmed
failing, then made to pass.

**Organization**: Tasks are grouped by user story (US1, US2) per spec.md's
priorities.

## Path Conventions

`.gitignore`, `backend/src/modules/eval/`,
`backend/tests/{unit,integration}/`, `backend/data/eval/` (created at
runtime, not by any task).

---

## Phase 1: Setup

**Purpose**: Module scaffolding and a real, pre-existing bug this
feature would otherwise inherit

- [X] T001 [P] Create `backend/src/modules/eval/__init__.py` (empty
  module init, matching every other module's pattern)
- [X] T002 Fix `.gitignore`'s `/data/` entry to `/backend/data/` —
  verified via `git check-ignore` (research.md: `/data/` is anchored to
  the repo root and has never actually matched `backend/data/`, where
  `download_category()` and this feature's new eval sets/reports
  genuinely live, since every CLI in this project runs with `backend/`
  as its working directory). No test — a plain config fix, verify with
  `git check-ignore -v backend/data/eval/x` before and after.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The Eval Question/Set/Report data shapes — and their
JSON/markdown (de)serialization — are used by both `generate` and
`run`; neither story can produce or consume a real file without them.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

> **NOTE: Write T003 FIRST, confirm it FAILS, then implement.**

- [X] T003 [P] Write failing tests for the Eval Question/Set/Report
  schemas in `backend/tests/unit/test_eval_schemas.py` — cover:
  `EvalSet.save()` writes `data/eval/sets/<department>-<timestamp>.json`
  (contracts/file-formats.md's shape) and `EvalSet.load(path)` round-trips
  it exactly (department, generated_at, questions_per_document, every
  question's question/expected_answer/source_document_title); saving
  two eval sets for the same department produces two distinct files,
  neither overwriting the other (FR-004); `EvalReport.to_markdown()`
  produces the header block (eval_set_path, run_at, k), an Aggregate
  Metrics table (hit_rate, mrr, answer_accuracy shown with
  judged_count), and one Per-Question Results row per Eval Result — a
  row with `retrieved=False` shows no rank; a row with
  `judged_correct=None` shows its `failure_reason` and leaves the
  Judged Correct cell blank, distinct from an actual ❌ (contracts/file-formats.md's
  blank-vs-❌ distinction, FR-010)
- [X] T004 Implement `backend/src/modules/eval/schemas.py`
  (`EvalQuestion`, `EvalSet` with `save()`/`load()`, `EvalResult`,
  `EvalReport` with `to_markdown()`) to make T003 pass (depends on T003)

**Checkpoint**: Eval sets/reports can be represented, saved, loaded,
and rendered. Neither `generate` nor `run` can actually produce one yet.

---

## Phase 3: User Story 1 - Generate a fixed evaluation set from ingested content (Priority: P1)

**Goal**: An operator runs `generate --department X` and gets a saved,
reusable eval set synthesized from that department's real ingested
content.

**Independent Test**: Run `generate` against a department with ingested
documents and confirm a saved eval set exists with one or more
questions per document, each carrying an expected answer and its
source document's identity.

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T005 [P] [US1] Write failing tests for reading a department's
  ingested content in `backend/tests/integration/test_eval_repository.py`
  — real Postgres — cover: returns every document (title) currently
  ingested in a department, each with its chunks' text in
  `chunk_order`; returns nothing for a department with no ingested
  documents; never returns another department's documents/chunks
- [X] T006 [US1] Implement `backend/src/modules/eval/repository.py`
  (`list_documents_with_chunks(conn, department) -> dict[str, list[str]]`,
  keyed by document title) to make T005 pass (depends on T005)
- [X] T007 [P] [US1] Write failing tests for question generation in
  `backend/tests/unit/test_eval_question_gen.py` — Ollama client mocked
  (matching `tests/unit/test_chat_generation.py`'s existing
  `client_factory` injection pattern, research.md) — cover: given a
  chunk of text, returns an `(question, expected_answer)` pair parsed
  from the model's structured JSON reply; a reply that isn't valid,
  well-shaped JSON raises a dedicated `QuestionGenerationError` rather
  than crashing or returning something unparsed
- [X] T008 [US1] Implement `backend/src/modules/eval/question_gen.py`
  (`generate_question(chunk_text, *, model, host, client_factory)`,
  `QuestionGenerationError`) to make T007 pass (depends on T007)
- [X] T009 [P] [US1] Write failing tests for `generate_eval_set()` in
  `backend/tests/unit/test_eval_service.py` — repository and
  question_gen both mocked — cover: for each document the (mocked)
  repository returns, samples up to `questions_per_document` of its
  chunks (evenly spaced across the document, so a small
  `questions_per_document` still covers the document's span rather than
  clustering at the start) and calls `generate_question()` once per
  sampled chunk, tagging each resulting `EvalQuestion` with that
  document's title; a document whose sampled chunks all raise
  `QuestionGenerationError` contributes zero questions, not a crash
  (Edge Cases); when the repository returns nothing for the department,
  raises a dedicated `NoIngestedContentError` *before* attempting to
  save anything (Edge Cases, US1 Scenario 3); on success, saves the
  built `EvalSet` (`schemas.py`'s `save()`) and returns its path
- [X] T010 [US1] Implement
  `generate_eval_set(department, *, questions_per_document, conn,
  repository, question_gen, settings_factory)` in
  `backend/src/modules/eval/service.py` (`NoIngestedContentError`) to
  make T009 pass (depends on T006, T008, T009)
- [X] T011 [P] [US1] Write failing tests for the `generate` CLI
  subcommand in `backend/tests/unit/test_eval_cli.py` —
  `generate_eval_set` mocked — cover: `generate --department sporting`
  calls it, prints the saved path, exits `0`; `--questions-per-doc`
  defaults to `3` when omitted and is passed through when given; a
  `NoIngestedContentError` is caught and mapped to a clear stderr
  message and exit code `1`, per contracts/cli.md
- [X] T012 [US1] Implement the `generate` subcommand in
  `backend/src/modules/eval/cli.py` (argparse subparsers — the first
  multi-action CLI in this project, per contracts/cli.md) to make T011
  pass (depends on T010, T011)

**Checkpoint**: User Story 1 is fully functional and independently
testable — SC-001 holds.

---

## Phase 4: User Story 2 - Run the evaluation and get a scored report (Priority: P1)

**Goal**: An operator runs `run --eval-set <path>` and gets a saved,
scored report — per-question retrieval/answer correctness plus
aggregate metrics — from replaying that fixed set through the real,
unmodified chat pipeline.

**Independent Test**: Run the evaluation against a previously generated
eval set and confirm a report is produced containing, for every
question, whether its source document was retrieved and whether the
answer was judged correct, plus summary metrics for the whole set.

> **NOTE: Write these tests FIRST, confirm they FAIL, then implement.**

- [X] T013 [P] [US2] Write failing tests for judging in
  `backend/tests/unit/test_eval_judge.py` — Ollama client mocked —
  cover: given an expected answer and a generated answer, returns
  `True`/`False` parsed from the model's structured JSON reply; a reply
  that isn't valid, well-shaped JSON raises a dedicated `JudgingError`
  rather than crashing or defaulting to a guess
- [X] T014 [US2] Implement `backend/src/modules/eval/judge.py`
  (`judge_answer(expected_answer, generated_answer, *, model, host,
  client_factory)`, `JudgingError`) to make T013 pass (depends on T013)
- [X] T015 [P] [US2] Write failing tests for `run_eval()` in
  `backend/tests/unit/test_eval_service.py` (extend) —
  `EvalSet.load()`, `modules.chat.retrieval.retrieve_relevant_chunks`,
  `modules.chat.generation.generate_answer`, and `judge_answer` all
  mocked — cover: for every question, calls the real (mocked)
  retrieval function with the question text, exactly as a real chat
  request does (FR-005, FR-012); marks a question `retrieved=True` with
  the correct 1-indexed `rank` when `source_document_title` appears
  among the mocked retrieval results' `document_title` values,
  `retrieved=False`/`rank=None` otherwise; when generation raises, the
  question is recorded with `generated_answer=None`, a
  `failure_reason`, `judged_correct=None`, and the run continues to the
  next question (FR-013); when judging raises, likewise recorded with
  `judged_correct=None` and a `failure_reason`; computes `hit_rate` and
  `mrr` over *all* questions but `answer_accuracy`/`judged_count` only
  over questions with a non-`None` `judged_correct` (FR-010); raises a
  dedicated `EvalSetNotFoundError` when the named path doesn't exist,
  *before* any retrieval call is made; on success, saves the built
  `EvalReport` (`schemas.py`'s markdown render) and returns its path
- [X] T016 [US2] Implement `run_eval(eval_set_path, *, retrieval,
  generation, judge, settings_factory)` in
  `backend/src/modules/eval/service.py` (extend) (`EvalSetNotFoundError`)
  to make T015 pass (depends on T004, T014, T015)
- [X] T017 [P] [US2] Write failing tests for the `run` CLI subcommand
  in `backend/tests/unit/test_eval_cli.py` (extend) — `run_eval` mocked
  — cover: `run --eval-set <path>` calls it, prints the saved report
  path plus the aggregate metrics, exits `0`; an `EvalSetNotFoundError`
  is caught and mapped to a clear stderr message and exit code `1`;
  omitting `--eval-set` is an argparse usage error, not a crash
- [X] T018 [US2] Implement the `run` subcommand in
  `backend/src/modules/eval/cli.py` (extend) to make T017 pass (depends
  on T016, T017)

**Checkpoint**: User Stories 1 AND 2 both fully functional — SC-002,
SC-003, and SC-004 hold; a full generate-then-run cycle produces a
scored report.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation against real ingested content and a
running Ollama, plus full-suite regression check

- [X] T019 [P] Run the full `quickstart.md` validation with real
  ingested content and Ollama running, confirming FR-001–FR-013 /
  SC-001–SC-005, documenting results in this tasks.md file

  **Results (live-validated against a real backend, real Postgres, real
  Ollama, 2026-08-09):**
  - Steps 1–2 (generate, twice): both produced real, grounded questions
    from real ingested content, in two distinct timestamped files.
    Confirmed.
  - Step 3 (empty department): exited `1` with a clear message, no file
    created. Confirmed.
  - Steps 4–5 (run, twice against the same set): both produced distinct
    reports; the report's Generated Answer/Judged Correct columns were
    genuinely populated from real retrieval + real generation + real
    judging. Confirmed.
  - Step 6 (nonexistent eval set): exited `1`, no report created.
    Confirmed.
  - Step 7 (single-question failure resilience): validated via the 4
    dedicated unit tests in `test_eval_service.py`
    (retrieval/generation/judging failure, each independently continuing
    the run) — consistent with quickstart.md's own note that forcing
    this deterministically live isn't practical.
  - Step 8 (chat unchanged): a real `/v1/chat` request against the same
    ingested content, before and conceptually unaffected by this
    feature's code, streamed a correct, normal answer — no behavior
    change. Confirmed.
  - **Real, non-bug finding surfaced during this validation**: the
    local judge model (`llama3.2`) genuinely misjudged an obviously
    correct generated answer as incorrect in one run (visible in that
    run's report). This is expected per spec.md's own Assumptions
    ("measures directionally, not as certified ground truth") — not a
    defect in this feature, and improving judge-prompt quality is
    explicitly out of scope for this baseline (see the note this
    finding prompted below).
  - **Real gap found and fixed during this validation**: the above
    finding was only catchable *because* the generated answer was
    visible in the report — except it initially wasn't.
    `EvalReport.to_markdown()` never rendered the `generated_answer`
    field at all, even though data-model.md always specified it as
    part of `EvalResult`. Fixed by adding a "Generated Answer" column
    (with `|`/newline escaping, since model text can contain either) —
    updated `schemas.py`, `contracts/file-formats.md`, and added 2 new
    tests (`test_eval_schemas.py`) confirming the column's presence and
    escaping.
  - Cleanup: all test accounts, ingested documents, eval sets, and
    reports created during this validation were removed afterward.
- [X] T020 Run the full backend test suite (`pytest`), confirm no
  regressions in previously-passing tests (Constitution's CI
  requirement), and re-confirm this project's established CI-parity
  discipline: the backend unit suite still passes with no `.env`/env
  vars at all

  **Results:** backend `pytest` — 242 passed. No-`.env`/no-env-var
  import of `src.modules.eval.service` (the new module with the widest
  import chain — pulls in `chat.service`/`chat.retrieval`/`chat.generation`
  transitively) — succeeds.
- [X] T021 Bump `VERSION`/`frontend/package.json`/`backend/src/__init__.py`
  and add a linked `CHANGELOG.md` entry, per the constitution's
  Development Workflow rule

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: No dependency on Setup's tasks
  specifically, but conventionally follows it — BLOCKS both user
  stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion
  and on `modules/eval/service.py`/`cli.py` already existing
  (T010/T012) since it adds to those same files rather than creating
  them from scratch
- **Polish (Phase 5)**: Depends on both user stories being complete

### Within Each User Story

- Tests MUST be written and confirmed failing before their
  corresponding implementation task (Constitution Principle I)
- Repository/generation-primitive tasks before the service-layer task
  that composes them, before the CLI task that exposes them
- User Story 2 reuses `modules/chat/retrieval.py`/`generation.py`
  unchanged (FR-012) — no task in this feature modifies either file

---

## Parallel Example: Foundational + User Story 1 kickoff

```bash
# These touch different files and can be written together once
# Foundational (T003/T004) is done:
Task: "Write failing tests for reading a department's ingested content in backend/tests/integration/test_eval_repository.py"
Task: "Write failing tests for question generation in backend/tests/unit/test_eval_question_gen.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks both stories)
3. Complete Phase 3: User Story 1 (`generate`)
4. **STOP and VALIDATE**: Confirm a real eval set gets produced from
   real ingested content
5. A saved eval set with no way to score it isn't independently
   valuable to a user the way most P1-only MVPs are — but it *is* a
   clean, demoable checkpoint the way this feature's tasks are ordered

### Incremental Delivery

1. Complete Setup + Foundational → eval set/report shapes exist,
   nothing produces one yet
2. Add User Story 1 → `generate` works end-to-end → validate
3. Add User Story 2 → `run` works end-to-end against a real generated
   set → validate — this is the point the feature is actually usable
   for its stated purpose (measuring the naive baseline)
4. Each story adds value without breaking the previous one

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing
- Commit after each task or logical group, split by conventional type
  (feat/test/chore), per this session's established pattern
- Stop at any checkpoint to validate a story independently
