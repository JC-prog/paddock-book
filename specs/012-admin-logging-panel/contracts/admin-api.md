# Contract: Admin API

Base path: `/v1/admin`. Every address here requires a valid
`Authorization: Bearer <access_token>` header whose account has
`is_admin: true` — matching the existing auth scheme from feature 007
(`core/security.py::get_current_user`), extended by a new
`require_admin` dependency.

## `GET /v1/admin/settings/log-destination`

Returns the currently active log-destination setting.

**Response** `200 OK`:

```json
{ "log_to_file": true }
```

If no row exists yet in `app_settings` (fresh install), this reflects
`Settings.log_to_file`'s `.env`-based default (feature 011) — the
response always has a concrete value, never `null`.

## `PUT /v1/admin/settings/log-destination`

Changes the setting. Takes effect the next time the backend application
starts (FR-006) — the response confirms the value was durably saved, not
that it's live in the current process.

**Request**:

```json
{ "log_to_file": false }
```

**Response** `200 OK`:

```json
{ "log_to_file": false }
```

On success, records a `log_destination_changed` event (see
`data-model.md`) naming the admin and the new value.

## Error responses (both addresses)

| Status | When |
|---|---|
| `401 Unauthorized` | No valid `Authorization` header (existing `get_current_user` behavior). |
| `403 Forbidden` | Valid session, but `is_admin` is `false`. |
| `422 Unprocessable Entity` | `PUT` body is missing `log_to_file` or it isn't a boolean. |

## Non-goals

- No endpoint here ever grants admin access to any account — that's
  exclusively `modules/admin/cli.py` (see `contracts/cli.md`), per
  FR-009.
- No endpoint here controls anything beyond this one setting — not a
  general settings API.
