# Contract: JSON Log Line Schema

Every log line is one JSON object, written to stdout. See
`data-model.md` for the field-by-field breakdown; this documents the
worked shapes for each of the three record kinds this feature produces.

## Request log — success

```json
{
  "timestamp": "2026-08-08T14:32:01.123Z",
  "level": "INFO",
  "logger": "src.core.middleware",
  "message": "request completed",
  "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "method": "POST",
  "path": "/v1/chat",
  "status_code": 200,
  "duration_ms": 842.3
}
```

## Request log — unhandled error

```json
{
  "timestamp": "2026-08-08T14:33:10.456Z",
  "level": "ERROR",
  "logger": "src.core.middleware",
  "message": "unhandled exception",
  "request_id": "8c1b2e10-9e3a-4b7a-9a2e-1f6d3c8b0a11",
  "method": "GET",
  "path": "/v1/health",
  "status_code": null,
  "duration_ms": 12.7,
  "exc_info": "Traceback (most recent call last): ..."
}
```

## Auth event log

```json
{
  "timestamp": "2026-08-08T14:34:00.000Z",
  "level": "WARNING",
  "logger": "src.modules.auth.service",
  "message": "login failed",
  "request_id": "9d2e4a10-1234-4b7a-9a2e-1f6d3c8b0a22",
  "event": "login_failed",
  "email": "driver@team.example",
  "user_id": null
}
```

`event` is one of: `login_succeeded`, `login_failed`, `logout_succeeded`,
`registration_succeeded`.

## Chat event log

```json
{
  "timestamp": "2026-08-08T14:35:00.000Z",
  "level": "INFO",
  "logger": "src.modules.chat.router",
  "message": "chat retrieval succeeded",
  "request_id": "1a2b3c4d-5678-4b7a-9a2e-1f6d3c8b0a33",
  "event": "chat_retrieval_succeeded",
  "user_id": "2b33916a-1a8c-4bee-a64b-59f9df0b3023",
  "departments": ["sporting"]
}
```

## Guarantees

- `request_id` is present and identical across every log line produced
  while handling one request (FR-003).
- No line of any kind ever contains a `password`, `password_hash`, access
  token, or refresh token value (FR-006).
- No chat event log line ever contains the question or answer text
  (FR-008).
- Field names and the `event` enum values above are stable — anything
  parsing these logs later can rely on them without renegotiation.

## Consumers

None inside this feature — these logs are read by an engineer directly
(via `docker compose logs`, or CloudWatch once deployed), not queried
programmatically by any other part of the application. This schema is
documented so that changes to it are deliberate, not accidental drift.
