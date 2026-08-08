# Quickstart: Application Logging

## Prerequisites

- Backend running locally (`uvicorn src.main:app --reload`, same as any
  other feature in this repo).
- A terminal watching the backend process's stdout.

## Steps

1. **Request + correlation ID (FR-001, FR-003)**

   ```
   curl -s http://localhost:8000/health
   ```

   **Expected**: one JSON log line appears on stdout with
   `"method": "GET", "path": "/health", "status_code": 200"` and a
   `request_id`. Matches `contracts/log-schema.md`'s request-log-success
   shape.

2. **Unhandled error (FR-002)**

   Temporarily trigger a real backend error (e.g. stop the local Postgres
   container, then hit an endpoint that needs it — `POST /v1/auth/login`
   with any credentials).

   **Expected**: an `ERROR`-level log line appears with `status_code:
   null` and an `exc_info` stack trace, and the HTTP response is still a
   clean `5xx` — the request doesn't hang or crash the server process.

3. **Auth events, and no password in the logs (FR-004, FR-006)**

   ```
   curl -s -X POST http://localhost:8000/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"nobody@example.com","password":"whatever-secret-123"}'
   ```

   **Expected**: a `WARNING`-level `login_failed` event log line appears
   with `email: "nobody@example.com"`. Confirm by eye that the literal
   string `whatever-secret-123` does not appear anywhere in that line or
   any other line on stdout.

   Then register and log in with a real account (per
   `specs/007-user-authentication/quickstart.md` if one exists, or
   `POST /v1/auth/register` directly) and confirm `registration_succeeded`
   and `login_succeeded` event lines appear, followed by a
   `logout_succeeded` line after `POST /v1/auth/logout`.

4. **Chat event, no message content in the logs (FR-005, FR-008)**

   Log in, then:

   ```
   curl -s -N -X POST http://localhost:8000/v1/chat \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{"message":"How many wheels must a car have?"}'
   ```

   **Expected**: a `chat_retrieval_succeeded` event log line appears with
   the account's `user_id` and `departments`. Confirm by eye that neither
   `"How many wheels must a car have?"` nor any fragment of the generated
   answer appears in that line or anywhere else on stdout.

5. **Request correlation across a multi-step request**

   Repeat step 4 and find all log lines sharing that request's
   `request_id` (the general request-log line for `POST /v1/chat`, and
   the `chat_retrieval_succeeded` event line). **Expected**: both carry
   the identical `request_id` value, letting them be tied together
   (FR-003, SC-005).

## Cleanup

None — this feature produces stdout output only, nothing persisted to
clean up.
