# Contract: Chat Provider Admin API

Base path: `/v1/admin`. Both addresses below require a valid
`Authorization: Bearer <access_token>` header whose account has
`is_admin: true` (existing `require_admin` dependency, feature 012) —
same enforcement as every other `/v1/admin/*` endpoint.

## `GET /v1/admin/settings/chat-provider`

Returns the currently active chat provider and every provider's saved
settings — except the API key's value, which is never returned (FR-011).

**Response** `200 OK`:

```json
{
  "active_provider": "ollama",
  "ollama_model_override": null,
  "bedrock_model": null,
  "openai_compatible_base_url": null,
  "openai_compatible_model": null,
  "openai_compatible_api_key_set": false
}
```

If no row exists yet (fresh install), this reflects the table's defaults
(`active_provider: "ollama"`, everything else `null`/`false`) — the
response always has concrete values, never a missing field, matching the
existing `log-destination` endpoint's "always a concrete value" behavior.

## `PUT /v1/admin/settings/chat-provider`

Updates the configuration. **Partial update, not full replace**: any
field present in the request body is changed; any field omitted keeps
its previously stored value. This is a deliberate deviation from strict
REST `PUT` semantics (documented in research.md) — it's what lets an
admin switch `active_provider` back to a previously configured provider
without resending that provider's API key (FR-015), since the key is
never sent back to the frontend in the first place (FR-011) and so the
frontend has no value to resend.

**Request** (all fields optional — send only what's changing):

```json
{
  "active_provider": "openai_compatible",
  "openai_compatible_base_url": "https://api.openai.com/v1",
  "openai_compatible_api_key": "sk-...",
  "openai_compatible_model": "gpt-4o-mini"
}
```

To activate a previously-configured provider without changing its saved
settings, send only the field being changed:

```json
{ "active_provider": "bedrock" }
```

**Response** `200 OK` — same shape as the `GET` response, reflecting the
row *after* the update:

```json
{
  "active_provider": "openai_compatible",
  "ollama_model_override": null,
  "bedrock_model": null,
  "openai_compatible_base_url": "https://api.openai.com/v1",
  "openai_compatible_model": "gpt-4o-mini",
  "openai_compatible_api_key_set": true
}
```

Takes effect immediately (SC-001) — the very next `POST /v1/chat` request
reads this row fresh, not a cached value (no application restart
involved, FR-006/FR-008).

### Activation validation (FR-012, FR-013)

If the request would result in `active_provider = 'openai_compatible'`
without `openai_compatible_base_url`, `openai_compatible_api_key`, and
`openai_compatible_model` **all** already present (from this request or
previously stored) — or `active_provider = 'bedrock'` without
`bedrock_model` present — the update is rejected and **nothing is
changed**:

**Response** `409 Conflict`:

```json
{ "detail": "openai_compatible requires a base URL, API key, and model name before it can be activated" }
```

(or the equivalent Bedrock-specific message when `bedrock_model` is
missing.)

## Error responses (both addresses)

| Status | When |
|---|---|
| `401 Unauthorized` | No valid `Authorization` header (existing `get_current_user` behavior). |
| `403 Forbidden` | Valid session, but `is_admin` is `false`. |
| `422 Unprocessable Entity` | Request body has the wrong shape (e.g. `active_provider` isn't one of the three known values, or a field is the wrong type). |
| `409 Conflict` | (`PUT` only) The requested `active_provider` would be missing required settings — see Activation validation above. |

## Non-goals

- No endpoint here ever calls out to Ollama, Bedrock, or an
  OpenAI-compatible service to validate a saved key or model — spec
  Assumptions explicitly exclude live validation at save time. A wrong
  API key or nonexistent model name is only discovered when a real
  `POST /v1/chat` request using that provider fails.
- No endpoint here changes `settings.embedding_provider` or anything else
  about embedding generation (FR-014) — this contract governs
  chat-generation provider selection only.
- No endpoint here manages AWS credentials for Bedrock — those remain
  exactly as externally managed as they are today (spec Assumptions).
