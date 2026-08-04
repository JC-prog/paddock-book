# API Contract: `POST /v1/chat`

Streamed via Server-Sent Events (`sse-starlette`'s `EventSourceResponse`, per
research.md). Unauthenticated (FR-006). Documented in prose rather than
OpenAPI YAML since the response is a streamed event sequence, not a single
JSON body.

## Request

```http
POST /v1/chat HTTP/1.1
Content-Type: application/json

{"message": "hello there"}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `message` | string | yes | Rejected if missing, empty, or whitespace-only (FR-002) |

## Success response

`200 OK`, `Content-Type: text/event-stream`. One SSE event per word of the
fixed placeholder reply, in order, then the connection closes:

```text
data: Hello,

data: this

data: is

data: a

data: test

data: response.

```

The stream ending (no further `data:` lines, connection closed) is the
completion signal per FR-005 — there is no separate `event: done` marker in
this feature; a client detects completion the same way it detects the end of
any closed HTTP stream.

## Rejected request (empty/whitespace-only message)

`422 Unprocessable Entity` (FastAPI's standard validation-error response for
a request body that fails the `ChatRequest` schema's non-empty constraint),
`Content-Type: application/json`. No SSE stream is opened — this is a normal
JSON error response, not an event stream, since no valid request was ever
accepted (FR-002, Acceptance Scenario 4).

## Client disconnect mid-stream

No response body — the server stops emitting further events for that request
once it detects the client is gone (via `request.is_disconnected()`) and
does not raise an unhandled error (Acceptance Scenario 5).

## Contract guarantees

- The reply is **always** delivered as more than one discrete event for a
  valid request (SC-005) — never as a single event containing the whole
  placeholder string.
- The placeholder content is fixed: "Hello, this is a test response." —
  independent of the request's `message` content (spec Assumptions).
- Any future change to the request shape, the event content, or the
  rejection behavior is a contract change: this file and its corresponding
  test (`backend/tests/unit/test_chat.py`) MUST be updated together
  (Constitution Principle III).
