# API Contract: `/v1/auth/*`

Four endpoints: `register`, `login`, `logout`, `refresh`. The access token
travels in the JSON response body (the frontend holds it in memory only,
research.md); the refresh token travels only as an httpOnly cookie — it
never appears in a JSON response body.

## `POST /v1/auth/register`

```http
POST /v1/auth/register HTTP/1.1
Content-Type: application/json

{"email": "driver@team.example", "password": "correct horse battery staple", "department": "sporting"}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `email` | string | yes | Rejected if already registered (FR-008) |
| `password` | string | yes | Rejected only if empty (FR-012) — no other complexity rule |
| `department` | string | yes | One of `sporting`, `technical`, `financial` (FR-006) |

**Success**: `201 Created`, `Content-Type: application/json`, plus a
`Set-Cookie: refresh_token=...; HttpOnly; SameSite=Lax; Path=/v1/auth`
header (`Secure` is added too whenever `COOKIE_SECURE=true`, which MUST be
set once actually deployed over HTTPS — it defaults to `false` for local
dev, since a `Secure` cookie is silently dropped by the browser, and by
`TestClient`, over plain `http://localhost`):

```json
{
  "access_token": "eyJ...",
  "user": {"id": "...", "email": "driver@team.example", "department": "sporting"}
}
```

**Rejected** (duplicate email, empty password, or invalid department):
`422 Unprocessable Entity`, `Content-Type: application/json`, standard
FastAPI validation-error shape. No cookie is set; no account is created.

## `POST /v1/auth/login`

```http
POST /v1/auth/login HTTP/1.1
Content-Type: application/json

{"email": "driver@team.example", "password": "correct horse battery staple"}
```

**Success**: `200 OK`, same body/cookie shape as `register`'s success
response.

**Rejected** (wrong password, or email with no account): `401 Unauthorized`
with a single generic error message that does not distinguish between the
two cases (FR-002, SC-003). No cookie is set.

## `POST /v1/auth/refresh`

No request body — relies entirely on the `refresh_token` cookie sent
automatically by the browser.

**Success**: `200 OK`. Response body contains a new `access_token`; the
`Set-Cookie` header replaces the refresh cookie with a newly-rotated one
(research.md — the old refresh token is revoked in the same operation).

**Rejected** (missing, expired, or already-revoked refresh token): `401
Unauthorized`. No new cookie is set — the frontend treats this the same as
"not logged in" and routes to `/login`.

## `POST /v1/auth/logout`

No request body — relies on the `refresh_token` cookie.

**Success**: `204 No Content`. The matching `refresh_tokens` row is revoked
server-side (FR-003 — this is what makes logout a real revocation, not
just a client-side action), and the response clears the cookie
(`Set-Cookie: refresh_token=; Max-Age=0; ...`).

If no valid refresh cookie is present, this still returns `204` — logging
out when already logged out is a no-op, not an error.

## Contract guarantees

- The refresh token is **never** present in a JSON response body — only as
  an httpOnly cookie. A response body containing anything named
  `refresh_token` would be a contract violation.
- `login` and `register`'s failure responses never reveal whether a given
  email address has an account (`login`: identical error for wrong password
  vs. unknown email; `register`: the duplicate-email error is the one
  intentional exception, since FR-008 requires the client to know a
  duplicate happened in order to fix the input).
- Every successful `refresh` rotates the refresh token — the previous one
  is revoked in the same request that issues the new one.
- Any future change to these request/response shapes, status codes, or
  cookie behavior is a contract change: this file and
  `backend/tests/integration/test_auth_api.py` MUST be updated together
  (Constitution Principle III).
