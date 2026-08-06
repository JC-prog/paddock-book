# Phase 0 Research: PDF Regulation Ingestion Pipeline

No `NEEDS CLARIFICATION` markers remain in the Technical Context. Both
clarifications from `/speckit-clarify` were resolved in spec.md. This
document records the supporting technical decisions needed to execute the
plan.

## Decision: `pypdf` 6.14.2 for PDF text extraction

- **Rationale**: Pure-Python, permissive BSD-3-Clause license, actively
  maintained, no native build step (unlike some C-extension-backed PDF
  libraries). FIA regulation PDFs are expected to be primarily linear,
  numbered-paragraph text rather than complex multi-column layouts or
  data-heavy tables, so `pypdf`'s straightforward text extraction is
  sufficient without needing layout-aware parsing.
- **Alternatives considered**: `PyMuPDF`/`fitz` — faster and more accurate,
  but AGPL-licensed; using it in this internal (but not open-sourced)
  product would require either open-sourcing the whole app or purchasing a
  commercial license, neither of which fits here. `pdfplumber` — better
  layout/table extraction (built on `pdfminer.six`), but heavier dependency
  chain for accuracy this feature doesn't need yet; worth reconsidering if
  ingestion quality issues turn out to be layout-related.

## Decision: `boto3` 1.43.65 for the Bedrock Titan V2 embedding call

- **Rationale**: The standard, first-party AWS SDK — already the natural
  choice given every embedding-related decision so far (feature 005's
  schema, the DeepSeek/Bedrock discussion) has assumed Bedrock. Calls
  `bedrock-runtime`'s `InvokeModel` for `amazon.titan-embed-text-v2:0` with
  `dimensions: 1024`, matching the column feature 005 already provisioned.
- **Alternatives considered**: A lighter-weight direct HTTP client instead
  of the full `boto3` SDK — rejected; `boto3` handles AWS request signing,
  retries, and credential resolution (env vars, shared config, IAM role)
  correctly out of the box, and a hand-rolled HTTP client would just be
  reimplementing that.

## Decision: `pydantic-settings` 2.14.2 in `backend/src/core/config.py`

- **Rationale**: This is the first backend code that actually needs
  `DATABASE_URL` (and AWS region config) in application logic — exactly
  the trigger point flagged in earlier discussion for introducing `core/`.
  `pydantic-settings` gives validated, typed config read from `.env`,
  matching FastAPI's own recommended pattern, rather than another ad-hoc
  `os.environ.get(...)` call like the one already living in the feature
  005 integration test (which is fine to leave as-is — it's a test, not
  application code).
- **Alternatives considered**: Plain `os.environ.get()` scattered across
  `repository.py`/`embeddings.py` — rejected; with a second real consumer
  of `DATABASE_URL` about to exist (this feature plus the next), scattering
  ad-hoc env reads is exactly the inconsistency a centralized `Settings`
  object avoids.

## Decision: fixed-size word-count chunking with overlap, no tokenizer dependency

- **Rationale**: Per the spec.md clarification, chunking is fixed-size, not
  article-boundary-aware. Implemented as a sliding window over
  whitespace-tokenized words — target ~500 words per chunk, ~75-word
  (~15%) overlap between consecutive chunks so context isn't lost at a
  boundary. These are reasonable, widely-used RAG starting defaults (per
  spec.md's own Assumptions), not exact token counts, so no tokenizer
  library (e.g. `tiktoken`) is needed — word count is a close enough proxy
  for this stage and avoids an extra dependency.
- **Alternatives considered**: A real tokenizer for token-accurate chunk
  sizing — more precise, but adds a dependency and complexity to hit a
  target that's explicitly a tunable starting point (spec.md Assumptions),
  not a hard requirement; can be revisited once retrieval quality is
  actually measurable.

## Decision: duplicate-title check happens first, before parsing or embedding

- **Rationale**: FR-007 requires rejecting a re-ingestion of an existing
  title. Checking this first (a cheap `SELECT` against `documents`) before
  doing any PDF parsing or — more importantly — any billed Bedrock
  embedding calls avoids wasted cost and time on a run that's going to be
  rejected anyway.
- **Alternatives considered**: Checking for the duplicate only at write
  time (after parsing/embedding) — simpler to implement but wastes Bedrock
  calls and parsing time on every accidental re-run; rejected as needlessly
  costly given the check is nearly free to do first.

## Decision: all embeddings generated in memory before any DB write; single transaction for the write

- **Rationale**: FR-008 requires all-or-nothing writes. The service
  generates every chunk's embedding first, collecting results in memory;
  only once all of them succeed does it open one `psycopg` transaction and
  write the document plus every chunk together, committing once at the
  end. If any embedding call fails, the run aborts before touching the
  database at all — nothing to roll back. If a write-time error occurs
  (e.g. an unexpected constraint violation), the single transaction's
  rollback-on-exception handles it the same way.
- **Alternatives considered**: Writing each chunk as it's embedded
  (streaming inserts) — would need explicit compensating deletes on
  failure partway through; rejected as more complex for no benefit at this
  document-at-a-time scale (per spec.md, one document per run).

## Decision: `argparse` for the CLI, no new dependency

- **Rationale**: The CLI takes exactly three inputs — file path, title,
  department — a textbook case for Python's standard-library `argparse`.
  No need for a heavier CLI framework (e.g. `click`/`typer`) for something
  this small.
- **Alternatives considered**: `click`/`typer` — nicer ergonomics for
  larger CLIs with subcommands, but unjustified for a single-command
  three-flag tool (Constitution Principle IV).
