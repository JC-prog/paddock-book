# Phase 1 Data Model: Local Vector Database for Regulation Chunks

Two related tables, per spec.md's Key Entities and the FR-004 clarification.
No rows are created by this feature — both tables start empty; a future
ingestion feature populates them.

## documents

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `uuid` | Primary key, default `gen_random_uuid()` | Unique identifier for a source regulation document |
| `title` | `text` | `NOT NULL` | Human-readable title distinguishing one source document from another |
| `created_at` | `timestamptz` | `NOT NULL`, default `now()` | When this document record was created |

## document_chunks

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `uuid` | Primary key, default `gen_random_uuid()` | Unique identifier for this chunk |
| `document_id` | `uuid` | `NOT NULL`, `REFERENCES documents(id)` | The source document this chunk belongs to |
| `chunk_text` | `text` | `NOT NULL` | The chunk's text content |
| `embedding` | `vector(1024)` | `NOT NULL` | Embedding vector, sized for Titan Text Embeddings V2's default output (FR-003) |
| `department` | `department` (enum: `sporting`, `technical`, `financial`) | `NOT NULL` | Which FIA regulation section this chunk belongs to |
| `chunk_order` | `integer` | `NOT NULL` | This chunk's sequential position within its source document |
| `created_at` | `timestamptz` | `NOT NULL`, default `now()` | When this chunk record was created |

**Constraints**:
- `UNIQUE (document_id, chunk_order)` — no two chunks of the same document
  share a position (supports FR-003's ordering requirement and prevents
  accidental duplicate ingestion of the same chunk position).

**Relationships**: One `documents` row has many `document_chunks` rows
(one-to-many via `document_chunks.document_id`).

**Validation rules**: `department` is restricted to exactly the three
values named in the spec (`sporting`, `technical`, `financial`) via a
Postgres enum type, not free text — a value outside this set is rejected by
the database itself, not left to application-level validation.

**Lifecycle**: Both tables are created empty by this feature's SQL init
script and remain empty until a future ingestion feature (explicitly out of
scope here) writes to them. No update/delete behavior is defined by this
feature — chunk mutation semantics belong to whatever feature actually
performs ingestion.

**Not included in this feature**: any similarity-search index (HNSW/
IVFFlat) on `embedding` — see research.md's decision to defer that until
real data and query patterns exist.
