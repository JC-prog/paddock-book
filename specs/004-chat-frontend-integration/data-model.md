# Phase 1 Data Model: Chat Frontend-Backend Integration

## ChatMessage (extended)

Extends the `ChatMessage` introduced in feature 002 (`id`, `text`). Still
transient — held only in the frontend's in-memory signal, never persisted,
never sent as context to the backend (spec Assumptions).

| Field | Type | Description | Source |
|---|---|---|---|
| `id` | string | Unique identifier within the session (unchanged from feature 002) | feature 002 |
| `text` | string | Message content. For an assistant message, this grows as words arrive while `status === 'streaming'` | feature 002; FR-003 |
| `sender` | `'user' \| 'assistant'` | **New.** Distinguishes the user's own messages from backend replies, so `MessageBubbleComponent` can style them differently (FR-002) | FR-002 |
| `status` | `'complete' \| 'streaming' \| 'error'` | **New.** `'complete'` immediately for user messages; assistant messages start `'streaming'`, become `'complete'` when the stream ends cleanly (FR-004), or `'error'` on timeout/dropped connection (FR-005) | FR-004, FR-005 |

**Validation rules**: unchanged for user messages (non-empty after trim,
per feature 002's `ChatService.sendMessage`). Assistant messages are created
internally by `ChatService`, not user input, so no separate validation
applies to them.

**Lifecycle** (assistant message only):

```text
sent → streaming (text grows word by word) → complete
                                            └→ error (on 10s silence or dropped connection; partial text kept, per FR-006)
```

**Relationships**: A user message and its corresponding assistant reply are
two separate `ChatMessage` entries in the same list (adjacent, in send
order) — there is no explicit foreign-key link between them; adjacency in
the list is sufficient for this feature's scope (no multi-turn context, no
reordering).

## ChatService state (new, not persisted)

| Field | Type | Description | Source |
|---|---|---|---|
| `isSending` | `boolean` (signal) | `true` from the moment a message is sent until its reply reaches `'complete'` or `'error'`; drives FR-007 (blocks further sends) | FR-007 |
