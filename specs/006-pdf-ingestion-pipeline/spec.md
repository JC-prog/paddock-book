# Feature Specification: PDF Regulation Ingestion Pipeline

**Feature Branch**: `006-pdf-ingestion-pipeline`

**Created**: 2026-08-06

**Status**: Draft

**Input**: User description: "Build an ingestion pipeline that takes a manually-provided PDF regulation document, extracts and chunks its text, generates an embedding for each chunk via AWS Bedrock Titan Text Embeddings V2, and writes the chunks into the existing documents/document_chunks tables (feature 005). Runs as a local script against the local pgvector database for development, one document at a time per run. Each ingestion run is told which department (Sporting/Technical/Financial) the document belongs to. No automated PDF downloading or scraping — documents are manually placed/provided. Out of scope: retrieval, chat/generation wiring, automatic document discovery, and any scheduled or triggered runs."

## Clarifications

### Session 2026-08-06

- Q: Should chunking be fixed-size, or aligned to the regulation's article/section numbering? → A: Fixed-size chunks with overlap between consecutive chunks — simplest, lowest-risk starting point with no retrieval feature yet to prove out what granularity actually works; article-aware chunking can be layered in later once that's known to matter.
- Q: What happens when the same source document is ingested a second time? → A: Reject the run — the existing document must be manually removed first. Forces re-ingestion to be a deliberate act rather than something that can silently duplicate or overwrite data.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest a regulation PDF into the searchable knowledge base (Priority: P1)

As a backend developer, I want to run a local process against a regulation
PDF, telling it which department the document belongs to, so that its
content becomes searchable chunks in the database that future retrieval
work can query.

**Why this priority**: This is the entire feature. The database schema
(feature 005) exists but is empty — nothing else in the knowledge-assistant
pipeline (retrieval, grounded chat answers) can be built or demonstrated
until real regulation content actually lives in it.

**Independent Test**: Run the pipeline against a sample regulation PDF with
a department specified, then inspect the database directly and confirm a
new document record exists along with multiple chunk records linked to it,
each carrying a non-empty embedding — fully verifiable with no retrieval
code needed.

**Acceptance Scenarios**:

1. **Given** a valid PDF file and a department, **When** the pipeline runs,
   **Then** a new document record is created and one or more chunk records
   are written, each linked to that document, tagged with the given
   department, and carrying an embedding.
2. **Given** the PDF contains substantial text, **When** chunking occurs,
   **Then** the resulting chunks preserve the order they appeared in the
   source document.
3. **Given** the pipeline completes successfully, **When** a developer
   inspects the database afterward, **Then** the stored chunks collectively
   account for the document's content, with nothing silently dropped.
4. **Given** an invalid or unreadable file is provided, **When** the
   pipeline runs, **Then** it fails with a clear, actionable error and
   writes nothing to the database.
5. **Given** an unsupported or missing department value is provided,
   **When** the pipeline runs, **Then** it fails clearly before attempting
   to read the file or write anything.

---

### Edge Cases

- What happens when the PDF has no extractable text (e.g. a scanned image
  with no text layer) or is corrupted? The pipeline must fail clearly
  rather than silently writing zero or garbled chunks.
- What happens when generating an embedding fails partway through a run
  (e.g. a transient error calling the embedding provider)? No partial
  document/chunk data should be left behind — see FR-008.
- What happens when the same source document is ingested a second time?
  See FR-007 (resolved in Clarifications).
- What happens with an unusually large PDF (e.g. several hundred pages)?
  The pipeline must still complete rather than hanging indefinitely or
  exhausting memory, even if it takes longer.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a single PDF file and a department
  value (Sporting, Technical, or Financial) as input for one ingestion run,
  processing exactly one document per run.
- **FR-002**: The system MUST extract readable text from the provided PDF.
- **FR-003**: The system MUST split the extracted text into multiple
  fixed-size chunks (a target word/character count), with overlap between
  consecutive chunks so context isn't lost across a chunk boundary.
- **FR-004**: The system MUST generate an embedding for each chunk using
  the project's existing embedding provider (AWS Bedrock Titan Text
  Embeddings V2), matching the size the database already expects
  (feature 005).
- **FR-005**: The system MUST create one new document record representing
  the source PDF, and MUST write one chunk record per generated chunk,
  linked to that document, tagged with the given department, and
  preserving each chunk's order within the document.
- **FR-006**: The system MUST reject the run — before writing anything — if
  the provided file is invalid/unreadable, or if the department value isn't
  one of the three supported values.
- **FR-007**: When a document with the same title as an already-ingested
  document is submitted again, the system MUST reject the run — writing
  nothing — rather than duplicating or replacing the existing document's
  data. The existing document must be removed before that title can be
  ingested again.
- **FR-008**: If a run fails partway through, the system MUST NOT leave
  partial document or chunk data behind — either the full document and all
  its chunks are written, or none of them are.

### Key Entities

- **Document** *(extends feature 005's entity)*: This feature is what
  actually creates document records — one per successful ingestion run,
  representing one source PDF.
- **Document Chunk** *(extends feature 005's entity)*: This feature is what
  actually creates chunk records — the text, embedding, department, source
  document reference, and order come directly from this pipeline's output.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can ingest a typical regulation PDF into the
  local database with a single command/invocation.
- **SC-002**: 100% of chunks written by a successful run carry a
  correctly-sized embedding, verified through testing.
- **SC-003**: 100% of attempts to ingest with an invalid file or an
  unsupported department fail clearly, with zero rows written, verified
  through testing.
- **SC-004**: 100% of failed or interrupted runs leave no partial document
  or chunk data in the database, verified through testing.
- **SC-005**: 100% of attempts to ingest a document whose title already
  exists in the database are rejected without writing anything, verified
  through testing.

## Assumptions

- Documents are provided as local file paths — no automated downloading,
  scraping, or document discovery is in scope (per the input description).
  A future feature may add that; this one assumes the PDF is already on
  disk.
- Retrieval (querying stored chunks) and wiring any of this into the chat
  interface are explicitly out of scope for this feature — this pipeline
  only gets content into the database.
- No scheduled or automatically-triggered runs are in scope — every
  ingestion run is manually invoked by a developer.
- The document's title is provided as part of the ingestion input rather
  than auto-derived from the PDF filename, since filenames tend to produce
  inconsistent or unhelpful titles.
- This feature runs against the local pgvector database set up in feature
  005. Running it against a hosted production database is a deliberate,
  separate operational decision, not something this feature automates.
- No authentication or access control is introduced — this is a
  locally-invoked developer tool, consistent with the rest of the local
  storage/dev-environment work so far.
- A document's title is treated as its identity for duplicate detection
  (FR-007) — it's already a required ingestion input (see above), so no
  separate identifier scheme is needed for this first version.
- The exact target chunk size and overlap amount are implementation
  details appropriate for planning, not a scope decision — general RAG
  chunking practice (chunks of a few hundred words, with modest overlap)
  is the starting point, refined during `/speckit-plan` if needed.
