# Research: Application Logging

## JSON log formatting

**Decision**: A small hand-rolled `logging.Formatter` subclass
(`core/logging.py::JsonFormatter`) that emits one JSON object per line:
`timestamp`, `level`, `logger`, `message`, `request_id` (when set), plus
whatever else was passed via a log call's `extra={...}`.

**Rationale**: The shape needed is simple and stable; a ~20-line formatter
avoids adding a third-party dependency (e.g. `python-json-logger`) for
something this small, consistent with this project's general preference
for the standard library when it's sufficient (e.g. `httpx` was reused
instead of adding `requests` in feature 009).

**Alternatives considered**: `structlog` — more powerful (context
binding, processors) but a new dependency and a different logging idiom
than the stdlib `logging` calls already implicitly expected by FastAPI's
own internals; not justified for this feature's scope.

## Request correlation ID

**Decision**: A `contextvars.ContextVar[str | None]` (`core/logging.py::
request_id_var`), set to a fresh UUID4 by `RequestLoggingMiddleware` at
the start of every request, read directly by `JsonFormatter.format()` at
emit time — so every log record produced while handling that request —
anywhere in the call stack, including inside `modules/auth/service.py` or
`modules/chat/router.py` — automatically carries it without threading a
`request_id` parameter through every function signature (FR-003).

**Rationale**: `contextvars` is the standard mechanism for request-scoped
state in ASGI apps — each request runs in its own asyncio Task with its
own copy of the context, so concurrent requests' IDs don't leak into each
other. This is verified directly in `tasks.md`'s middleware tests (two
overlapping requests, asserting each only sees its own ID).

**Alternatives considered**: Passing `request_id` explicitly through every
function call — rejected as invasive (would touch nearly every function
signature in `auth`/`chat`) for something that's naturally request-scoped
context, not business data.

Not exposed to the client via a response header — nothing in spec.md
requires client-visible correlation, and adding one would be a new,
unrequested capability.

## Where request-level logging happens

**Decision**: A single `BaseHTTPMiddleware` (`core/middleware.py::
RequestLoggingMiddleware`) wraps every request: logs one INFO record on
successful completion (method, path, status, duration_ms), or one ERROR
record on an unhandled exception (method, path, duration_ms, exception
info via `exc_info=True`) before re-raising so FastAPI's normal 500
handling still applies. This single middleware satisfies FR-001, FR-002,
and (via the context var above) FR-003.

**Rationale**: A single choke point for every request is simpler and more
reliable than scattering logging calls across every route handler, and
matches the constitution's statement that `core/` owns cross-cutting
middleware.

**Alternatives considered**: A FastAPI exception handler for FR-002
instead of catching inside the middleware — rejected because it wouldn't
also give a natural, single place to compute request duration for both
the success and failure paths.

## What the middleware does NOT log

**Decision**: The middleware never inspects or logs request/response
headers or bodies — only method, path, status, and duration. It doesn't
touch `Authorization` or `Cookie` headers at all.

**Rationale**: This is the simplest way to guarantee FR-006 (no
credential material ever logged) for the general request log: there's
nothing to accidentally leak because nothing sensitive is ever read in
the first place, rather than relying on redaction logic that could have a
gap.

## Auth event logging — what counts as an "event"

**Decision**: `modules/auth/service.py` logs exactly four cases, matching
spec.md's FR-004 literally: successful login (INFO), failed login
attempt (WARNING — a security-relevant signal worth being visible without
being an application error), successful logout (INFO), and successful
registration (INFO). Each includes the account's email and, when known,
its user ID — never the password.

Failed registration (duplicate email, empty password) and token refresh
are deliberately NOT given their own dedicated event log. Failed
registration is already visible in the general request log (FR-001) via
its `422` status; a silent token refresh isn't one of the four events
FR-004 lists, and treating it as one would be new scope beyond what was
asked for.

**Rationale**: Matches spec.md's User Story 2 acceptance scenario exactly
("Perform a login, a failed login, a logout, and a chat request") — no
more, no less.

**Logout needs one small addition**: `logout()` currently only hashes the
incoming refresh token and calls `repository.revoke_refresh_token()` — it
never looks up which account the token belonged to. To log "which account
logged out" (FR-004), `logout()` now calls the already-existing
`repository.get_valid_refresh_token()` first (which returns `user_id`)
before revoking — no new repository function needed, no new query beyond
what a symmetric lookup-then-write already implies.

## Chat event logging — where it happens

**Decision**: Logged in `modules/chat/router.py::post_chat`, immediately
after `retrieve_context()` returns successfully — not inside
`retrieve_context()` itself. The router already has the full `user` dict
(id + department) and doesn't need `retrieve_context()`'s existing,
already-tested signature to change.

**Rationale**: Keeps `chat/service.py::retrieve_context()` (and its
existing unit tests from feature 008) untouched; the router is where the
"a chat request's retrieval succeeded" event is naturally observable
without extra plumbing.

Per feature 007's account model, an account has exactly one department,
and retrieval is scoped to the requester's own department — so today a
chat request's log entry will always show exactly one department. Spec.md's
edge case ("content spans more than one department") is forward-looking
robustness (the log field is a list, not a single value) rather than a
case that can occur with the system as it exists today.

A retrieval *failure* (the existing 502 path) does not produce this
chat-specific event log, since there's no "department retrieved" to
report — but it's still captured by the general request log (FR-001,
status 502), so SC-003's "100% of chat requests produce a log entry" is
satisfied by the combination of the two logs, not by the chat-specific
one alone covering failures too.

## Logging-failure resilience (FR-007)

**Decision**: `core/middleware.py::_log_safely()` wraps every logging
call the middleware makes in an explicit `try/except Exception: pass`.

**Rationale**: The original plan was to rely on the standard library's
own behavior — `StreamHandler.emit()` does catch failures in its own body
(write/flush) via `handleError()`. But `logging.Handler.handle()` itself
has no try/except around the `emit()` call, and `Logger.callHandlers()`
has none either (confirmed by reading the installed stdlib source
directly, not assumed) — so a handler failing more fundamentally than a
normal write error (e.g. its `emit` method itself being broken) still
propagates straight through `logger.info()`/`logger.error()` into the
caller. This was caught by `test_a_logging_handler_failure_does_not_fail_the_request`
actually failing against the "rely on stdlib" version of the middleware
before `_log_safely` was added — not discovered by inspection.

**Alternatives considered**: Trusting stdlib behavior alone — rejected
after the above test proved it insufficient for the general case FR-007
actually describes.
