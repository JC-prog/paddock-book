# Contract: `documents` / `document_chunks` Schema

This is the interface future features (chunking, embedding generation,
ingestion, retrieval) code against. Column-by-column detail lives in
[data-model.md](../data-model.md); the source of truth for the actual DDL is
`db/init/001_init_schema.sql`. This file documents the guarantees that DDL
provides.

## Contract guarantees

- The `vector` extension is enabled in the database — any code can use
  pgvector's `vector` type and its distance operators (`<->`, `<=>`, `<#>`)
  without enabling anything itself.
- `document_chunks.embedding` is a `vector(1024)` column. Inserting a vector
  of any other dimension MUST fail at the database level (pgvector enforces
  this), not silently truncate or pad.
- `document_chunks.department` only accepts `'sporting'`, `'technical'`, or
  `'financial'` — enforced by a Postgres enum type. Any other value MUST be
  rejected by the database.
- Every `document_chunks` row references an existing `documents` row via
  `document_id` — the foreign key MUST prevent orphaned chunks.
- `(document_id, chunk_order)` is unique — no future ingestion code can
  accidentally write two chunks claiming the same position in the same
  document.
- Both tables start empty. This feature provides no data and no code path
  that writes to them.

## Explicitly not part of this contract

- No similarity-search index exists on `embedding` yet (see research.md) —
  a future feature that adds one is not a breaking change to this contract,
  but is also not something callers can assume exists yet.
- No API endpoint exposes this schema — it is a direct database contract
  only, consumed by whichever backend code connects directly to Postgres.

## Changing this contract

Any change to column names, types, constraints, or the department enum's
values is a contract change: `data-model.md`, `db/init/001_init_schema.sql`,
this file, and `backend/tests/integration/test_schema.py` MUST be updated
together (Constitution Principle III).
