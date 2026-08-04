# Phase 1 Data Model: Chat API with Streamed Responses

Per spec.md's Key Entities, both shapes here are transient — request-scoped
only, never persisted, never stored (spec Assumptions).

## ChatRequest (request body)

| Field | Type | Description | Source requirement |
|---|---|---|---|
| `message` | string | The client's chat message | FR-001 |

**Validation rules**:
- `message` MUST be non-empty after trimming whitespace (FR-002) — a request
  failing this MUST be rejected rather than producing a placeholder reply.

## ChatReply (streamed SSE events, not a JSON response body)

Not a Pydantic response model — the reply is a sequence of plain-text SSE
events, not a single JSON object. Each event's `data` field is one word of
the fixed placeholder string.

| Field | Type | Description | Source requirement |
|---|---|---|---|
| `data` (per event) | string | One word of "Hello, this is a test response." | FR-004 |

**Sequencing**: five events, one per word of the placeholder ("Hello,",
"this", "is", "a", "test", "response." — split on whitespace), delivered in
order, followed by stream closure as the completion signal (FR-005).

**Lifecycle**: a `ChatRequest` and its resulting `ChatReply` events exist
only for the duration of one HTTP request; nothing is retained afterward
(spec Assumptions — no conversation history in this feature).

**Relationships**: none — no `Conversation` or `User` entity is in scope.
