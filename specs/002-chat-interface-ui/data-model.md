# Phase 1 Data Model: Chat Interface UI

Per spec.md's Key Entities section, this feature has exactly one entity, and it
is transient (never persisted, never sent over a network):

## ChatMessage

| Field | Type | Description | Source requirement |
|---|---|---|---|
| `id` | string | Unique identifier for the message within the current session (e.g. `crypto.randomUUID()`); used as the list-rendering track key | FR-005 |
| `text` | string | The message content the user typed, trimmed of leading/trailing whitespace | FR-005, FR-006 |

**Ordering**: not a stored field — a message's position in the `ChatMessage[]`
array (held by `ChatService`, see research.md) determines its render order in the
chatbox (FR-002). New messages are appended to the end of the array.

**Validation rules**:
- `text` MUST be non-empty after trimming whitespace (FR-006) — enforced in
  `ChatService.sendMessage()` before a `ChatMessage` is ever constructed, so no
  invalid `ChatMessage` can exist.

**Lifecycle**: created when the user submits a non-empty message (FR-005);
exists only in browser memory for the current page session; not persisted
across reload, not sent to any backend (spec Assumptions). There is no update
or delete operation on a `ChatMessage` in this feature.

**Relationships**: none — `ChatMessage` stands alone; there is no `User` or
`Conversation` entity in scope for this feature.
