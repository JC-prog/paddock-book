# Phase 1 Data Model: PDF Regulation Ingestion Pipeline

This feature writes to feature 005's existing schema — see that feature's
[data-model.md](../005-pgvector-local-dev/data-model.md) for the full column
definitions. No schema changes. This document covers only what's new: the
in-memory shapes this pipeline produces before writing.

## IngestionInput (CLI input, not persisted)

| Field | Type | Description | Source requirement |
|---|---|---|---|
| `file_path` | path | Local path to the PDF to ingest | FR-001 |
| `title` | string | The document's title — also its identity for duplicate detection | FR-005, FR-007 |
| `department` | `'sporting' \| 'technical' \| 'financial'` | Matches the existing `department` enum (feature 005) | FR-001 |

**Validation rules**: `file_path` MUST point to a readable file (FR-006);
`department` MUST be one of the three supported values (FR-006); a
`documents` row with the same `title` MUST NOT already exist (FR-007) —
all three checked before any parsing begins.

## Chunk (in-memory, produced by `chunker`, not yet embedded)

| Field | Type | Description |
|---|---|---|
| `text` | string | The chunk's text content |
| `order` | integer | Its position within the document (0-indexed, sequential) |

## EmbeddedChunk (in-memory, produced by `embeddings`, ready to write)

Extends `Chunk` with:

| Field | Type | Description |
|---|---|---|
| `embedding` | list of 1024 floats | Output of the Titan V2 call for this chunk's text |

## Write shape (what `repository` persists)

One `documents` row (`title`, `created_at` default) plus one
`document_chunks` row per `EmbeddedChunk` (`document_id` referencing the new
document, `chunk_text`, `embedding`, `department` from the ingestion input,
`chunk_order` from the chunk's `order`) — written together in a single
transaction (FR-008, research.md).

**Lifecycle**: `IngestionInput` → validated → PDF parsed → chunked →
every chunk embedded → all writes committed together, or none of them are.
There is no update path — `document_chunks` rows are never modified after
creation by this feature (re-ingestion of an existing title is rejected,
per FR-007, not merged/updated).
