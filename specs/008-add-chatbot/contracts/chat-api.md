# API Contract: `POST /v1/chat` (revised — supersedes feature 003's version)

Still streamed via Server-Sent Events (`sse-starlette`'s `EventSourceResponse`),
still one SSE event per fragment of the reply. What changes from feature 003:
the endpoint now requires authentication, and the streamed content is a real
generated answer (or an explicit "no relevant information" reply) instead of
a fixed placeholder string.

## Request

```http
POST /v1/chat HTTP/1.1
Content-Type: application/json
Authorization: Bearer <access_token>

{"message": "What tyre compounds are mandatory for a dry race?"}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `message` | string | yes | Rejected if missing, empty, or whitespace-only (feature 003, FR-002 — unchanged) |

The `Authorization` header carries the access token issued by feature 007's
`/v1/auth/login`/`/register`/`/refresh`. Its `department` claim determines
which regulation content this request's answer may draw from (FR-003).

## Success response

`200 OK`, `Content-Type: text/event-stream`. One SSE event per fragment of
the generated answer, in order, then the connection closes:

```text
data: For

data: dry

data: conditions,

data: Article

data: 12.4

data: requires...

```

The stream ending (no further `data:` lines, connection closed) is the
completion signal, unchanged from feature 003 — there is no separate
`event: done` marker.

## Unauthenticated request

`401 Unauthorized` (from `get_current_user`, feature 007), `Content-Type:
application/json`. No SSE stream is opened — this is a normal JSON error
response, not an event stream, since the request never reached the point of
generating anything (FR-001).

## No relevant content retrieved

Still `200 OK` with an SSE stream — not an error. The stream carries a fixed,
clear "no relevant information" reply instead of a generated one (FR-005).
The client cannot distinguish this from a normal generated answer at the
transport level; the distinguishing signal is the content itself.

## Rejected request (empty/whitespace-only message)

`422 Unprocessable Entity` — unchanged from feature 003.

## Retrieval failure (embedding call or database unreachable)

`502 Bad Gateway`, `Content-Type: application/json`. `200 OK` is never
reached — retrieval runs before the SSE stream opens specifically so this
failure surfaces as a clean error response, not a broken mid-stream
connection. The frontend's existing `!response.ok` check (feature 003/004)
already treats this the same as any other failed request — no frontend
change was needed to handle it.

## Generation (LLM) failure after the stream has already opened

If the failure happens once streaming has started (retrieval already
succeeded), the connection drops mid-stream instead. The staff member sees
the existing frontend failure-state indication (feature 004) — the same
failure UX already used for any dropped connection, not a new one.

## Contract guarantees

- The reply is **always** delivered as more than one discrete event for a
  valid, authenticated request — unchanged from feature 003's SC-005-derived
  guarantee.
- The endpoint is **never** reachable without a valid access token (FR-001) —
  this is new in this revision and supersedes feature 003's "unauthenticated,
  consistent with the rest of the skeleton" note, which was explicitly
  correct only until this feature shipped.
- Retrieved and generated content is **always** scoped to the requesting
  staff member's department (FR-003/FR-006) — content from another
  department is never included in the prompt sent to the LLM, not merely
  filtered from the response after the fact.
- Any future change to this request/response shape, the auth requirement, or
  the department-scoping guarantee is a contract change: this file and
  `backend/tests/unit/test_chat.py` MUST be updated together (Constitution
  Principle III).
