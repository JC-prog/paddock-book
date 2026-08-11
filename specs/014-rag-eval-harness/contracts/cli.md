# Contract: Eval Harness CLI

Two subcommands, mirroring `modules/ingestion/cli.py`'s/`modules/download/cli.py`'s
argparse style — the first multi-action CLI in this project, using
argparse subparsers rather than a second top-level script.

## `generate` — build a fixed eval set

```
python -m src.modules.eval.cli generate --department <sporting|technical|financial> [--questions-per-doc N]
```

| Flag | Required | Default | Notes |
|---|---|---|---|
| `--department` | Yes | — | Must be one of the three existing departments (`modules/ingestion/service.py::DEPARTMENTS`). |
| `--questions-per-doc` | No | `3` | How many chunks (research.md) to generate a question from per document. |

**Behavior**:

1. Reads every document currently ingested in `--department` (existing
   `documents`/`document_chunks` tables, read-only).
2. If none exist, prints a clear message to stderr and exits non-zero
   — no eval set file is created (spec.md Edge Cases).
3. For each document, samples up to `--questions-per-doc` chunks and
   generates one question+expected-answer per sampled chunk (research.md).
   A document whose generation fails entirely is skipped, not fatal to
   the run (Edge Cases).
4. Writes `data/eval/sets/<department>-<timestamp>.json`
   (data-model.md's Eval Set shape) and prints its path to stdout.

**Exit codes**: `0` on producing a file with at least one question;
`1` if there was nothing to generate from (no ingested documents, or
every document's generation failed).

## `run` — score a fixed eval set

```
python -m src.modules.eval.cli run --eval-set <path to a generate-produced .json file>
```

| Flag | Required | Default | Notes |
|---|---|---|---|
| `--eval-set` | Yes | — | No default/"most recent" inference (FR-005a) — must name an existing file produced by `generate`. |

**Behavior**:

1. Loads the named eval set. If the path doesn't exist, prints a clear
   error to stderr and exits non-zero without writing a report
   (spec.md Edge Cases).
2. For every question, calls the real, unmodified
   `modules/chat/retrieval.py::retrieve_relevant_chunks()` and
   `modules/chat/generation.py::generate_answer()` — the identical code
   path a real chat request already uses (FR-005, FR-012) — then judges
   the generated answer against the question's `expected_answer`
   (research.md).
3. A retrieval, generation, or judging failure for one question is
   recorded and excluded from the affected aggregate metric's
   denominator, never fatal to the run (FR-013).
4. Writes `data/eval/reports/<eval-set-stem>-<timestamp>.md`
   (data-model.md's Eval Report shape) and prints its path and the
   aggregate metrics to stdout.

**Exit codes**: `0` once a report is written, regardless of how many
individual questions failed (a report full of failures is still a
successful run of the tool — FR-013). `1` only if the named eval set
couldn't be loaded at all.

## Non-goals

- No UI or admin-panel surface — this is an operator-run CLI tool only
  (spec.md Assumptions).
- No durable run history — every invocation produces its own file;
  there's no database record and no way to list past runs through this
  tool (spec.md Assumptions).
- `run` never infers which eval set to use — always explicit
  (FR-005a).
