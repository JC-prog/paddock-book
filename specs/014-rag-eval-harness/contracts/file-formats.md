# Contract: Eval Set & Report File Formats

## Eval Set (`data/eval/sets/<department>-<timestamp>.json`)

```json
{
  "department": "sporting",
  "generated_at": "2026-08-09T12:00:00Z",
  "questions_per_document": 3,
  "questions": [
    {
      "question": "How many wheels must a car have?",
      "expected_answer": "Exactly four.",
      "source_document_title": "FIA 2026 F1 Regulations - Section B [Sporting] - Iss 08 - 2026-08-05"
    }
  ]
}
```

Field shapes match data-model.md's Eval Set / Eval Question tables
exactly. This file is machine-read by `run` — its shape is a contract
both commands must agree on, not just documentation.

## Eval Report (`data/eval/reports/<eval-set-stem>-<timestamp>.md`)

Markdown, meant for a person to read (not re-parsed by this tool):

```markdown
# Eval Report

**Eval set**: data/eval/sets/sporting-20260809-120000.json
**Run at**: 2026-08-09T12:05:00Z
**k**: 5

## Aggregate Metrics

| Metric | Value |
|---|---|
| Hit Rate@5 | 0.86 |
| MRR | 0.71 |
| Answer accuracy | 0.90 (18/20 judged) |

## Per-Question Results

| # | Question | Source Document | Retrieved | Rank | Generated Answer | Judged Correct | Failure |
|---|---|---|---|---|---|---|---|
| 1 | How many wheels must a car have? | FIA 2026 ... Section B ... | ✅ | 1 | Exactly four. | ✅ | |
| 2 | ... | ... | ❌ | — | An answer using the wrong context. | ❌ | |
| 3 | ... | ... | ✅ | 2 | — | — | judging: response was not valid JSON |
```

**Generated Answer** is included deliberately (added after live validation surfaced why it's necessary, not
just documentation): the judge is itself an LLM call, and it can — and, in local
testing, genuinely did — misjudge an obviously correct answer as
incorrect. Without the generated answer visible, a human reading the
report has no way to catch or sanity-check a bad judgment; a report
with a bare pass/fail column isn't actually usable for its stated
purpose. Long answers are flattened to one line and `|` characters are
escaped (`\|`) so model-generated text can never corrupt the table's
structure.

**Header block**: `eval_set_path`, `run_at`, `k` — data-model.md's Eval
Report top-level fields, sufficient for the report to be self-describing
without needing the original eval-set file open.

**Aggregate Metrics table**: `hit_rate`, `mrr`, `answer_accuracy` (shown
alongside `judged_count`/total so a reader can see how much of the set
was actually scorable — FR-010).

**Per-Question Results table**: one row per Eval Result
(data-model.md). A row with `Retrieved: ❌` has no `Rank`. A row with a
generation/judging failure shows it in the `Failure` column and leaves
`Judged Correct` blank rather than `❌` — blank is "excluded from the
metric," `❌` is "judged and found incorrect" (FR-010's distinction,
made visually unambiguous).
