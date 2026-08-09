# Quickstart: RAG Evaluation Harness

## Prerequisites

- The local database running with real ingested content in at least one
  department — see README.md's "Getting Real Content Into the
  Knowledge Base" section if starting from empty.
- `EMBEDDING_PROVIDER=ollama` in `backend/.env`, with both
  `ollama pull llama3.2` and `ollama pull mxbai-embed-large` already
  done (README.md's "Running Fully Locally" section) — question
  generation, real chat generation, and judging all use the same local
  Ollama model this feature reuses (research.md).

## Steps

1. **Generate a fixed eval set (FR-001–FR-004, US1)**

   ```
   cd backend
   python -m src.modules.eval.cli generate --department sporting --questions-per-doc 3
   ```

   **Expected**: exits `0`, prints the path to a new
   `data/eval/sets/sporting-<timestamp>.json`. Open it — it should have
   one entry per (document, sampled chunk), each with a `question`,
   `expected_answer`, and `source_document_title` matching a real
   ingested document's title.

2. **Generating again produces a second, independent file (FR-004, US1 Scenario 2)**

   Repeat step 1.

   **Expected**: a *second* `data/eval/sets/sporting-<a-later-timestamp>.json`
   — the first file from step 1 is untouched.

3. **Generating for an empty department fails cleanly (US1 Scenario 3)**

   ```
   python -m src.modules.eval.cli generate --department financial
   ```

   (assuming nothing's been ingested into `financial` yet)

   **Expected**: exits non-zero, a clear stderr message that there's
   nothing to generate from, no file created under `data/eval/sets/`.

4. **Run the evaluation and get a scored report (FR-005–FR-011, US2)**

   ```
   python -m src.modules.eval.cli run --eval-set data/eval/sets/sporting-<timestamp-from-step-1>.json
   ```

   **Expected**: exits `0`, prints the path to a new
   `data/eval/reports/sporting-<timestamp>-<run-timestamp>.md` plus the
   aggregate metrics. Open the report — confirm it has both the
   Aggregate Metrics table (Hit Rate@5, MRR, answer accuracy) and one
   Per-Question Results row per question in the eval set from step 1.

5. **Running the same eval set again produces its own independent report (FR-011, SC-003)**

   Repeat step 4 against the same eval-set path.

   **Expected**: a *second*, distinct report file — the first from step
   4 is untouched. This is the mechanism that will let a future
   reranking-enabled report be compared against today's naive-RAG
   baseline report side by side.

6. **Running against a nonexistent eval set fails cleanly (Edge Cases)**

   ```
   python -m src.modules.eval.cli run --eval-set data/eval/sets/does-not-exist.json
   ```

   **Expected**: exits non-zero, a clear stderr message that the file
   can't be found, no report created.

7. **A single bad question doesn't abort the run (FR-013, SC-004)**

   Hard to force deterministically end-to-end without actually breaking
   Ollama mid-run — validated primarily via the unit tests covering
   generation/judging failure handling (`tasks.md`). If you want to see
   it live: stop Ollama partway through a `run` invocation against a
   multi-question eval set, then restart it before the run finishes.
   **Expected**: the report still gets written, with the
   affected question(s) showing a `Failure` reason and excluded from
   `answer_accuracy`'s denominator, rather than the whole command
   crashing.

8. **Chat behavior is unchanged (FR-012, SC-005)**

   Ask a question in the chat UI (or via `curl`, per feature 008's
   quickstart) both before and after this feature's changes are
   deployed. **Expected**: identical behavior — this feature only reads
   `retrieve_relevant_chunks()`/`generate_answer()`'s existing outputs,
   never modifies them.

## Cleanup

`data/eval/` is gitignored, like `data/regulations/` — delete its
contents freely between runs if you don't want to keep old
sets/reports around locally.
