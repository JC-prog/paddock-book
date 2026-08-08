# Data Model: Application Logging

Logs are not persisted to a database — each "entity" here is the shape of
one JSON line written to stdout. See `contracts/log-schema.md` for the
exact, worked examples.

## Log Entry (common envelope)

Every log line, regardless of which of the two kinds below it is, shares
this envelope:

| Field | Type | Notes |
|---|---|---|
| `timestamp` | `str` | ISO 8601, UTC. |
| `level` | `str` | `INFO`, `WARNING`, or `ERROR`. |
| `logger` | `str` | The Python logger name (module path) that emitted it. |
| `message` | `str` | Short human-readable summary. |
| `request_id` | `str \| null` | The correlation ID for the request this happened during (Request Identifier, below); `null` for anything logged outside a request context (there is none in this feature's current scope, but the field stays nullable rather than assuming one always exists). |

## Request Log Entry (FR-001, FR-002)

Produced once per request by `RequestLoggingMiddleware`, extending the
common envelope with:

| Field | Type | Notes |
|---|---|---|
| `method` | `str` | HTTP method. |
| `path` | `str` | Request path. |
| `status_code` | `int \| null` | Response status; `null` when an unhandled exception occurred before a response was produced (the `ERROR`-level variant, FR-002). |
| `duration_ms` | `float` | Time spent handling the request. |
| `exc_info` | `str \| null` | Present only on the `ERROR`-level variant — the formatted exception/stack trace. |

## Auth Event Log Entry (FR-004, FR-006)

Produced by `modules/auth/service.py` for exactly four event kinds,
extending the common envelope with:

| Field | Type | Notes |
|---|---|---|
| `event` | `str` | One of `login_succeeded`, `login_failed`, `logout_succeeded`, `registration_succeeded`. |
| `email` | `str` | The account's email — the attempted email for `login_failed`, since there may be no matching account. |
| `user_id` | `str \| null` | The account's ID, when known (always known except for `login_failed` against a non-existent email). |

Never present: `password`, `password_hash`, any access or refresh token
value (FR-006) — these fields simply don't exist on this record; nothing
is redacted after the fact.

## Chat Event Log Entry (FR-005, FR-008)

Produced by `modules/chat/router.py` when a chat request's retrieval
succeeds, extending the common envelope with:

| Field | Type | Notes |
|---|---|---|
| `event` | `str` | Always `chat_retrieval_succeeded`. |
| `user_id` | `str` | The requesting account's ID. |
| `departments` | `list[str]` | Department(s) whose content was retrieved — always exactly one element given today's one-department-per-account model (see `research.md`), but a list so a future multi-department retrieval doesn't require a schema change. |

Never present: the question text, the generated answer text (FR-008).

## Request Identifier

A UUID4 string, generated fresh per request by `RequestLoggingMiddleware`
and held in a `contextvars.ContextVar` for the lifetime of that request's
handling. Not a persisted entity — it only exists to tie together every
Log Entry produced while one request was being handled (FR-003), and
appears as the `request_id` field on all of them.
