# Data Model: RAG Evaluation Harness

None of these are database tables — all three are file-serialized
shapes (spec.md Assumptions). `Eval Set` is stored as JSON (it's
re-read by `run`); `Eval Report` is rendered as markdown (it's meant to
be read by a person, not re-parsed by this tool).

## Eval Question

One synthesized test case (spec.md's Eval Question entity).

| Field | Type | Notes |
|---|---|---|
| `question` | `str` | The synthesized question text. |
| `expected_answer` | `str` | The synthesized expected answer, from the same generation call as `question` (research.md). |
| `source_document_title` | `str` | The `documents.title` the question was generated from — the ground truth for retrieval scoring (research.md's title-not-id decision). |

## Eval Set

A named, saved collection of Eval Questions from one `generate` run
(spec.md's Eval Set entity).

| Field | Type | Notes |
|---|---|---|
| `department` | `str` | The department `generate` was run against — `run` reads this from the file rather than taking a separate `--department` argument. |
| `generated_at` | `str` (ISO 8601) | Also embedded in the filename (research.md), but kept here too so the file is self-describing if renamed. |
| `questions_per_document` | `int` | The `--questions-per-doc` value used, for reproducibility context. |
| `questions` | `list[Eval Question]` | Every question this generation run produced. A document that failed generation (Edge Cases) simply contributes no questions — there's no placeholder/error entry in this list. |

**File location**: `data/eval/sets/<department>-<timestamp>.json`.

## Eval Report

The saved output of one `run` against one Eval Set (spec.md's Eval
Report entity).

| Field | Type | Notes |
|---|---|---|
| `eval_set_path` | `str` | Which Eval Set file this report was run against — printed in the report so it's self-describing. |
| `run_at` | `str` (ISO 8601) | Also embedded in the filename. |
| `k` | `int` | The retrieval limit used (research.md — imported from `chat/retrieval.py`, not redeclared). |
| `results` | `list[Eval Result]` | One entry per question in the Eval Set. |
| `hit_rate` | `float` | Aggregate — fraction of questions whose source document was retrieved at all (FR-009). |
| `mrr` | `float` | Aggregate — Mean Reciprocal Rank (FR-009). |
| `answer_accuracy` | `float` | Aggregate — `correct_count / judged_count`, excluding failed judgments from the denominator (FR-010). |
| `judged_count` | `int` | How many questions actually contributed to `answer_accuracy` — shown alongside it so a reader can see how much of the set was excluded. |

### Eval Result (one per question, within a report)

| Field | Type | Notes |
|---|---|---|
| `question` | `str` | Copied from the Eval Question for a self-contained report. |
| `source_document_title` | `str` | Copied from the Eval Question. |
| `retrieved` | `bool` | Whether `source_document_title` appeared anywhere in this question's top-k retrieval results. |
| `rank` | `int \| None` | 1-indexed position if retrieved, else `None` — the per-question basis for the aggregate MRR. |
| `generated_answer` | `str \| None` | What the real, unmodified chat generation pipeline produced. `None` if generation itself failed. |
| `judged_correct` | `bool \| None` | `True`/`False` if judging succeeded, `None` if generation or judging failed for this question (excluded from `answer_accuracy`'s denominator, per FR-010). |
| `failure_reason` | `str \| None` | Set when `generated_answer` or `judged_correct` is `None`, explaining why (Edge Cases / FR-013) — always visible in the per-question report detail even though excluded from the aggregate. |

**File location**: `data/eval/reports/<eval-set-stem>-<timestamp>.md`.

## Relationships

- An Eval Report references its Eval Set by file path (`eval_set_path`),
  not by embedding the questions again — the report's `results` list
  already carries everything from each Eval Question it needs
  (`question`, `source_document_title`) for the report to be
  self-contained and readable without also having the original file
  open.
- Neither Eval Set nor Eval Report references `documents`/`document_chunks`
  by id — only by `title` (research.md), consistent with not modifying
  `retrieve_relevant_chunks()`'s existing return shape.
