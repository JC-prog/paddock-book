# Phase 1 Data Model: Retrieval-Grounded Chat Answers

This feature reads feature 005/006's existing `documents`/`document_chunks`
tables — no schema change, no new tables. This document covers only the
in-memory shapes this feature introduces between retrieval and generation.

## RetrievedChunk (in-memory, produced by `retrieval.py`)

| Field | Type | Description |
|---|---|---|
| `chunk_text` | string | The regulation text this chunk contains |
| `document_title` | string | The source document's title (feature 006's `documents.title`) — used for citation |
| `distance` | float | Cosine distance from the question's embedding (`<=>` operator) — closer to 0 is more similar |

**Validation rules**: Every returned `RetrievedChunk` MUST come from a
`document_chunks` row whose `department` matches the requesting staff
member's department claim (FR-003) — enforced by the SQL `WHERE` clause, not
filtered after the fact.

## GenerationContext (in-memory, passed from `retrieval.py` to `generation.py`)

| Field | Type | Description |
|---|---|---|
| `question` | string | The staff member's original chat message |
| `chunks` | list of `RetrievedChunk` | Empty list when nothing was retrieved (empty department corpus) — `generation.py` short-circuits to the deterministic "no relevant information" response in this case (research.md), never calling the LLM |

## ChatAnswer (in-memory, streamed out by `generation.py`)

Not a single object — matching feature 003's existing design, the answer is
an async generator of text fragments, streamed to the client exactly as the
placeholder reply already was (feature 003), now carrying real generated
content (or the fixed "no relevant information" string) instead of the fixed
placeholder string.

## Relationship to existing entities

- `RetrievedChunk` is derived from `document_chunks` (feature 005/006) —
  read-only, no new columns, no new table.
- The requesting staff member's `department` (feature 007's JWT claim) is
  the filter key for retrieval — no new relationship to the `users` table is
  introduced; the claim is already present on every authenticated request.

**Lifecycle**: Created fresh per chat request; nothing here is persisted.
Matches feature 003's original design note: "unauthenticated, each request
handled independently with no shared state across concurrent chats" — this
feature adds authentication and department-scoping to that request, but
introduces no new persistence.
