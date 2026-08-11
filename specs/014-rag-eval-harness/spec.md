# Feature Specification: RAG Evaluation Harness

**Feature Branch**: `014-rag-eval-harness`

**Created**: 2026-08-09

**Status**: Draft

**Input**: User description: "Add a RAG evaluation harness so we can measure retrieval and answer quality now, on the naive/traditional RAG pipeline, and compare it against future retrieval improvements (e.g. reranking) using the same fixed test set. Two-phase CLI, mirroring the existing ingestion/download CLI pattern: (1) a \"generate\" command that uses an LLM to synthesize question/expected-answer pairs from the currently-ingested documents in a given department (a configurable number of questions per document, default a small handful), producing a fixed eval-set file saved to disk and reused across runs — critical because comparing \"naive vs reranking\" metrics only means something if both runs face the exact same questions; (2) a \"run\" command that replays that saved eval-set through the real, unmodified retrieval and generation pipeline (the same code path the chat feature already uses, completely unchanged by this feature), and for each question: checks whether the source document it was generated from appears among the retrieved chunks (retrieval correctness), and uses an LLM-as-judge to score whether the generated answer is correct against the expected answer from phase 1 (binary correct/incorrect, not a graded scale). Produces a markdown report with per-question results and aggregate metrics: Hit Rate@k and Mean Reciprocal Rank (MRR) for retrieval (k matching the same retrieval limit the real chat feature already uses), and an overall answer-accuracy percentage for generation. Reports are saved to disk as files (not a database table) so two reports — e.g. today's naive baseline and a future reranking run — can be compared by eye once a second retrieval approach exists. Both new LLM calls (question generation and judging) reuse whichever model/provider is already configured for chat generation (Ollama locally by default) — no new provider integration required. Out of scope: actually implementing reranking or any other retrieval improvement itself — this feature only builds the measurement tool; a UI or admin-panel surface for running or viewing evals — this stays a CLI tool, matching the ingestion/download pattern; persisting eval run history in a database — reports are just files for now; evaluating content beyond whatever is currently ingested in the database at generation time."

## Clarifications

### Session 2026-08-09

- Q: When an operator runs the evaluation, how do they specify which saved eval set to run it against? → A: The operator must explicitly name/point to which saved eval set to run (e.g. by its saved name or path) — `run` has no implicit "most recent" default.
- Q: If the answer-generation or judging step fails or can't confidently score a question, should that question still count in the answer-accuracy percentage as incorrect, or be excluded from the metric entirely? → A: Excluded from the metric, but still shown in the per-question report detail — a tooling failure isn't evidence the pipeline answered wrong.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate a fixed evaluation set from ingested content (Priority: P1)

An operator who has already ingested regulation documents into a department wants a repeatable set of test questions to measure retrieval and answer quality against. They run a command against that department's ingested documents, and the tool produces a saved set of test questions — each paired with its source document and an expected answer — derived from the real ingested content.

**Why this priority**: Without a fixed, reusable eval set, there's nothing to score against, and nothing to legitimately compare a later retrieval improvement (like reranking) to. This is the foundation everything else in this feature depends on.

**Independent Test**: Can be fully tested by running the generate step against a department with ingested documents and confirming a saved eval set exists with one or more questions per document, each carrying an expected answer and the identity of its source document.

**Acceptance Scenarios**:

1. **Given** documents are ingested in a department, **When** the operator runs the generate step for that department, **Then** a saved eval set is produced containing questions, each tied to exactly one source document and an expected answer.
2. **Given** the generate step is run twice for the same department, **When** the operator inspects the results, **Then** each run produces its own eval set rather than silently overwriting or merging with a prior one, so an earlier baseline set is never lost by accident.
3. **Given** a department has no ingested documents, **When** the operator runs the generate step for it, **Then** the tool reports clearly that there's nothing to generate from, rather than producing an empty or misleading eval set.

---

### User Story 2 - Run the evaluation and get a scored report (Priority: P1)

An operator who has a saved eval set wants to know how well the current retrieval-and-answer pipeline performs against it. They run the evaluation, and the tool asks every question in the eval set through the same pipeline real chat questions already go through, checks whether each question's source document was actually retrieved, judges whether the generated answer is correct, and produces a report summarizing both.

**Why this priority**: This is the actual measurement capability the feature exists for — an eval set alone, without a way to score against it, proves nothing. Equally load-bearing to User Story 1.

**Independent Test**: Can be fully tested by running the evaluation against a previously generated eval set and confirming a report is produced containing, for every question, whether its source document was retrieved and whether the answer was judged correct, plus summary metrics across the whole set.

**Acceptance Scenarios**:

1. **Given** a saved eval set, **When** the operator runs the evaluation, **Then** a report is produced showing, per question, whether the source document was retrieved and whether the generated answer was judged correct.
2. **Given** a completed evaluation run, **When** the operator views the report, **Then** it also shows aggregate retrieval and answer-quality metrics summarizing the whole set, not just per-question detail.
3. **Given** the same eval set is evaluated twice (e.g. once today, once after a future retrieval change), **When** the operator compares the two reports, **Then** both are saved as their own distinct files so they can be compared side by side.

---

### Edge Cases

- What happens when the underlying answer-generation or judging step fails for a question (e.g. the model is unreachable)? Recorded as a failure for that question in the per-question report and excluded from the answer-accuracy metric's denominator (not counted as incorrect), rather than aborting the whole evaluation run or silently skewing the metric.
- What happens when the eval set references a document that's since been deleted from the knowledge base? Treated as a retrieval miss for that question, since the document is genuinely no longer retrievable.
- What happens if generating a question from a particular document fails (e.g. the document's text is empty or unusable)? That document is skipped for question generation rather than aborting the whole generate run.
- What happens if the operator points the evaluation at an eval set that doesn't exist? The tool reports clearly that it can't find that eval set, rather than silently falling back to a different one.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST let an operator generate a fixed evaluation set of test questions from the documents currently ingested in a specified department.
- **FR-002**: Each generated question MUST be paired with the single source document it was derived from and an expected answer.
- **FR-003**: System MUST let the operator control how many questions are generated per document, with a small default if not specified.
- **FR-004**: Each generation run MUST produce its own saved eval set, never silently overwriting a previously generated one.
- **FR-005**: System MUST let an operator run a previously generated eval set through the same retrieval-and-answer pipeline used by real chat questions, unmodified by this feature.
- **FR-005a**: The operator MUST explicitly identify which saved eval set to run against — the system MUST NOT infer or default to "the most recently generated one," so that comparing two runs (e.g. a naive baseline against a future reranking run) is guaranteed to be against the identical set, not accidentally against different ones.
- **FR-006**: For each question, the system MUST determine whether its source document appears among the documents retrieved for it.
- **FR-007**: For each question, the system MUST judge whether the generated answer is correct against the expected answer, recording a binary correct/incorrect result.
- **FR-008**: System MUST produce a report for each evaluation run containing both per-question results and aggregate retrieval and answer-quality metrics for the whole set.
- **FR-009**: Aggregate retrieval metrics MUST include how often the correct document was retrieved at all, and how highly it tended to be ranked when it was.
- **FR-010**: Aggregate answer-quality metrics MUST include the overall proportion of questions answered correctly, computed only over questions that were successfully judged — a question whose generation or judging failed MUST be excluded from this metric's denominator (not counted as incorrect), while still appearing in the per-question report detail with its failure noted.
- **FR-011**: Each evaluation run MUST produce its own saved report, so multiple runs against the same eval set (e.g. before and after a future retrieval change) can be compared afterward.
- **FR-012**: System MUST NOT alter the existing chat retrieval or answer-generation behavior — this feature only measures it.
- **FR-013**: A failure generating or judging any single question MUST NOT abort the rest of a generation or evaluation run.

### Key Entities *(include if feature involves data)*

- **Eval Question**: One synthesized test case — its question text, source document, and expected answer.
- **Eval Set**: A named, saved collection of Eval Questions produced by one generation run, tied to the department it was generated from.
- **Eval Report**: The saved output of one evaluation run against one Eval Set — per-question retrieval/correctness results plus aggregate metrics.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can produce a usable eval set from any department with ingested content without writing any test questions by hand.
- **SC-002**: An operator can get a scored report — both per-question detail and summary metrics — from a single command run against a saved eval set.
- **SC-003**: Two evaluation runs against the same eval set produce two independently reviewable reports, with nothing about running the second overwriting or altering the first.
- **SC-004**: A single failed question during generation or evaluation never prevents the rest of the run from completing and being reported.
- **SC-005**: The retrieval and answer-generation behavior real chat users experience is unchanged after this feature ships.

## Assumptions

- The evaluation reuses whichever LLM provider/model is already configured for chat generation (e.g. Ollama locally) for both question generation and answer judging — no new provider integration.
- Retrieval correctness is judged at the document level (was the source document among the retrieved chunks), not at the exact chunk level, since chunk boundaries are an implementation detail of ingestion, not something a test question is written against.
- This is an operator-run tool (a CLI), not a UI or admin-panel surface, matching how the existing ingestion and download pipelines are already operated.
- Eval sets and reports are files, not database records — there's no requirement here to query or list past runs through an API.
- Judging "correct" vs "incorrect" is inherently approximate (an LLM judging another LLM's answer) — this feature measures directionally, not as a certified ground truth, and that limitation is expected to be understood by whoever reads a report.
