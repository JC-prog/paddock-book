# Research: RAG Evaluation Harness

## Question generation works per-chunk, not per-document

**Decision**: For each document in the target department, `generate`
samples up to `--questions-per-doc` of that document's real
`document_chunks` rows and makes one LLM call per sampled chunk, asking
it to produce one question answerable from that chunk's text plus its
expected answer. All questions from a document are tagged with that
document's title as their source document.

**Rationale**: Real FIA regulation documents (feature 009) run to dozens
of pages — concatenating a whole document into one LLM call risks
exceeding context and produces vague, unfocused questions. A single
~500-word chunk (feature 006's chunking) is exactly the unit retrieval
actually searches over, so a question grounded in one chunk is
realistic: it's the same size/shape of content a real retrieved result
would be. Document-level ground truth (spec.md Assumptions) means it
doesn't matter which of a document's chunks a question came from for
scoring purposes — only that the right document comes back.

**Alternatives considered**: Generating from the whole document text at
once — rejected for the context-size and vagueness reasons above.

## Source document identity is the document title, not its id

**Decision**: An Eval Question's source document is recorded as
`documents.title` (a string), and retrieval correctness is checked by
whether that title appears among `retrieve_relevant_chunks()`'s
returned `document_title` values.

**Rationale**: `modules/chat/retrieval.py::retrieve_relevant_chunks()`
already returns `document_title` per result, not `document_id` — and
FR-012 requires this feature to call that function completely
unmodified, exactly as real chat requests do. Using title as the join
key needs no change to retrieval at all. `modules/ingestion/service.py`
already enforces title uniqueness at ingest time (`title_exists()`
check), so title is a reliable identifier in practice, not just a
display string.

**Alternatives considered**: Adding `document_id` to
`retrieve_relevant_chunks()`'s return shape — rejected; it would be a
change to production retrieval code motivated purely by this
measurement tool's convenience, which is exactly the kind of scope
creep FR-012 exists to prevent.

## `run` reuses `modules/chat/service.py`'s orchestration functions, not the lower-level retrieval/generation modules directly

**Decision** (refined during implementation, correcting plan.md's
original framing): `run_eval()` calls
`modules/chat/service.py::retrieve_context()` and `::generate_reply()`
— the exact two functions `modules/chat/router.py`'s real `POST
/v1/chat` handler calls — not `modules/chat/retrieval.py`/`generation.py`
directly.

**Rationale**: `retrieve_context()` is where the embed-then-retrieve
wiring and the psycopg-error-to-RuntimeError translation actually live;
calling `retrieval.py` directly would mean reimplementing that glue in
this feature, which is exactly the kind of "not quite the same code
path" gap FR-012 exists to avoid. Verified directly against
`chat/router.py`: `conn = get_connection(); chunks =
retrieve_context(message, department, conn=conn); return
EventSourceResponse(generate_reply(message, chunks))` — this is the
literal, complete real pipeline these two functions already are.

**Consequence for connection handling**: `retrieve_context()` closes
the connection it's given in its own `finally` block (it's written for
one connection per request). `run_eval()` therefore opens a fresh
connection per question via `connection_factory=get_connection`, the
same way a real chat request gets its own connection per HTTP call —
this is a feature of faithfully simulating independent requests, not a
workaround.

**Consequence for failure handling**: `retrieve_context()` can raise
(wrapped as `RuntimeError`, matching `chat/router.py`'s own `except
RuntimeError` handling). Spec.md's Edge Cases explicitly named
generation/judging failures as non-fatal to the run (FR-013); a
retrieval failure is the same class of problem and is handled
identically — recorded against that question with a `failure_reason`,
`retrieved=False`, `judged_correct=None`, and the run continues.

## Question generation, answer generation, and judging all reuse the one existing LLM integration

**Decision**: All three LLM-calling steps — synthesizing a question,
the real chat answer (via `modules/chat/generation.py::generate_answer()`,
unmodified), and judging that answer — call the same local Ollama chat
model already configured for chat (`Settings.ollama_model`/`ollama_host`),
using the same `client_factory`-injected `ollama.AsyncClient`/`Client`
pattern `generate_answer()` already established, mockable in unit tests
the same way `tests/unit/test_chat_generation.py` already does.

**Rationale**: This codebase's chat *generation* step has never had a
provider switch — only embeddings do (`EMBEDDING_PROVIDER`
bedrock/ollama, `core/embeddings.py`). There is no second generation
provider to choose between here; reusing the existing integration is
the only option that doesn't add a new one, matching spec.md's
Assumptions ("no new provider integration").

**Alternatives considered**: Using a separate/more-capable model
specifically for judging, to reduce same-model self-grading bias —
raised and explicitly decided against during pre-specify planning: this
feature measures directionally, not as certified ground truth (spec.md
Assumptions), and introducing a second model would itself be a new
provider integration this feature explicitly stays out of.

## Question-gen and judge prompts request structured output, parsed defensively

**Decision**: Both new LLM calls ask for a small JSON object in the
reply (`{"question": ..., "expected_answer": ...}` for generation;
`{"correct": true/false}` for judging). A reply that doesn't parse as
valid, well-shaped JSON is treated as that step's failure — the
document is skipped for generation (Edge Cases), or the question is
excluded from the answer-accuracy denominator for judging (FR-010) —
never a crash, per FR-013.

**Rationale**: Free-text LLM output is harder to parse reliably than a
small requested JSON shape, and a parse failure gives an unambiguous,
easy-to-detect "this step failed" signal to route into the
already-specified failure handling, rather than guessing at intent from
prose.

**Alternatives considered**: Parsing free-text answers with regex/string
heuristics — rejected as more fragile, not more capable, for a
same-model-family setup that already follows structured-output
instructions reasonably reliably.

## Eval sets and reports are timestamped files, never reused paths

**Decision**: `generate --department X` writes
`data/eval/sets/<department>-<YYYYMMDD-HHMMSS>.json`. `run --eval-set <path>`
writes `data/eval/reports/<eval-set-stem>-<YYYYMMDD-HHMMSS>.md`. Neither
command infers a default target — `run` requires `--eval-set <path>`
explicitly (FR-005a).

**Rationale**: A timestamp in the filename mechanically satisfies
FR-004/FR-011 ("never silently overwrite a previous one") without any
extra bookkeeping, and requiring the explicit `--eval-set` path is
exactly what FR-005a's clarification decided — no "most recent" default
that could silently compare two different runs against different
underlying question sets.

## Retrieval metrics reuse the real feature's own k, not a redeclared constant

**Decision**: `run_eval()` imports `RETRIEVAL_LIMIT` from
`modules/chat/retrieval.py` directly as the `k` for Hit Rate@k and MRR,
rather than defining its own constant.

**Rationale**: The whole point of this tool is measuring what real chat
users actually experience (FR-005). If the real feature's retrieval
limit ever changes, an eval-harness constant that drifted out of sync
would silently measure the wrong thing. Importing the real constant
makes that impossible.

**Metric definitions**:
- **Hit Rate@k**: the fraction of questions whose source document title
  appears anywhere in that question's top-k retrieved results.
- **MRR** (Mean Reciprocal Rank): the mean, across all questions, of
  `1 / rank` where `rank` is the 1-indexed position of the source
  document's first appearance in the top-k results (already ordered by
  ascending distance — i.e. best match first — by
  `retrieve_relevant_chunks()`), or `0` if it doesn't appear at all.
- **Answer accuracy**: `correct_count / judged_count`, where
  `judged_count` excludes any question whose generation or judging step
  failed (FR-010) — never counted as incorrect, per the clarification
  session.

## `.gitignore`'s existing `/data/` entry doesn't actually cover where data lives

**Decision**: This feature's tasks include fixing the repo-root
`.gitignore`'s `/data/` entry to `/backend/data/` (or equivalent), not
just adding a new entry for `data/eval/`.

**Rationale**: Verified directly (`git check-ignore`): `/data/` in the
repo-root `.gitignore` is anchored to the repo root, so it only ever
matched a `data/` directory that would sit next to `backend/`/`frontend/`
— it has never actually covered `backend/data/regulations/`, where
downloaded/ingested content genuinely lives (every CLI in this project,
including this feature's, runs with `backend/` as its working
directory, per README's `cd backend && ...`). This is the same class of
bug fixed for `backend/.env` in the local-Ollama-demo-setup fix — a
path assumed relative to the repo root that's actually resolved
relative to `backend/`. `data/eval/` (this feature) would inherit the
identical gap if not corrected now.

## No new database schema

**Decision**: `modules/eval/repository.py` only reads the existing
`documents`/`document_chunks` tables (feature 001) — no migration, no
new table.

**Rationale**: Eval sets and reports are files, not database records
(spec.md Assumptions) — there is nothing for this feature to persist
in Postgres beyond reading the content that already exists there.
