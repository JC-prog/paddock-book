# Data Model: Chat Provider Configuration

## `chat_provider_settings` (new table)

A singleton table — exactly one row, `id = 1` — following the same
pattern as the existing `app_settings` table (feature 012). Combines the
spec's two conceptual entities (Chat Provider Configuration, Provider
Credential) into one row, since both are exactly-one-instance-ever data
(see research.md — Storage decision).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `smallint` | `PRIMARY KEY DEFAULT 1 CHECK (id = 1)` | Always `1` — enforces the singleton, matching `app_settings`. |
| `active_provider` | `text` | `NOT NULL DEFAULT 'ollama' CHECK (active_provider IN ('ollama', 'bedrock', 'openai_compatible'))` | Which provider chat generation currently uses. Defaults to `ollama` so a fresh install behaves exactly as this codebase does today, with zero configuration required (spec Assumptions). |
| `ollama_model_override` | `text` | nullable | Optional model name overriding this project's default `OLLAMA_MODEL` setting. `NULL` means "use the default" (FR-006). |
| `bedrock_model` | `text` | nullable | Bedrock model identifier to `converse_stream` against. Required (non-null, non-empty) before `active_provider` can be set to `'bedrock'` (FR-005, FR-013). |
| `openai_compatible_base_url` | `text` | nullable | Base URL for the OpenAI-compatible connection. Required before `active_provider` can be `'openai_compatible'` (FR-004, FR-012). |
| `openai_compatible_api_key` | `text` | nullable | Stored as **plain text** — a deliberate, documented tradeoff (spec FR-010, Assumptions), not an oversight. Required before `active_provider` can be `'openai_compatible'`. Never included in any API response (FR-011) — see `contracts/admin-api.md`. |
| `openai_compatible_model` | `text` | nullable | Model name sent on every OpenAI-compatible chat-completions request. Required before `active_provider` can be `'openai_compatible'` (FR-004, FR-012). |
| `updated_at` | `timestamptz` | `NOT NULL DEFAULT now()` | Set on every update — supports User Story 3's "confirm a prior change took effect." |

### Validation rules (enforced in `admin/service.py`, not as DB constraints — see research.md)

- Setting `active_provider = 'bedrock'` requires `bedrock_model` to already
  be non-null and non-empty in the resulting row (after merging the
  request's partial update onto the current stored row) — otherwise the
  update is rejected with `IncompleteProviderConfigError` (FR-013).
- Setting `active_provider = 'openai_compatible'` requires
  `openai_compatible_base_url`, `openai_compatible_api_key`, and
  `openai_compatible_model` to all be non-null and non-empty in the
  resulting row — otherwise rejected the same way (FR-012).
- Setting `active_provider = 'ollama'` has no prerequisite — always
  allowed (FR-006, Assumptions: Ollama needs no credential).
- A `PUT` may change `active_provider` and a provider's settings in the
  same request (e.g. supply `bedrock_model` for the first time *and* set
  `active_provider` to `'bedrock'` in one call) — validation runs against
  the fully-merged resulting row, not the pre-update row.

### Lifecycle

No state machine — this is a settings row updated in place. It is
created (with all-default values) the first time
`GET`/`PUT /v1/admin/settings/chat-provider` runs against a database that
doesn't have the row yet, mirroring `get_log_destination_setting`'s
existing "row may not exist yet, fall back to defaults" handling for
`app_settings`.

## Read shape consumed by `chat/generation.py`

Not a new table — a plain in-memory value object
(`ChatProviderConfig`, e.g. a `dataclass`) that `chat/service.py`
builds from the `chat_provider_settings` row (via
`admin.repository.get_chat_provider_settings(conn)`) and passes into
`generate_answer()`. Shape:

| Field | Type | Populated from |
|---|---|---|
| `provider` | `Literal["ollama", "bedrock", "openai_compatible"]` | `active_provider` |
| `ollama_model` | `str` | `ollama_model_override` if set, else the existing `Settings().ollama_model` default |
| `ollama_host` | `str` | Existing `Settings().ollama_host` (unchanged — not admin-configurable per this feature's scope) |
| `bedrock_model` | `str \| None` | `bedrock_model` |
| `aws_region` | `str` | Existing `Settings().aws_region` (unchanged — AWS credentials/region remain externally managed, per spec Assumptions) |
| `openai_compatible_base_url` | `str \| None` | `openai_compatible_base_url` |
| `openai_compatible_api_key` | `str \| None` | `openai_compatible_api_key` |
| `openai_compatible_model` | `str \| None` | `openai_compatible_model` |

This keeps `generation.py` free of any Postgres/`Settings` dependency of
its own (Constitution Principle V) — it only ever sees a fully-resolved
configuration object, matching `generate_answer`'s existing style of
taking plain `model`/`host` arguments rather than reaching for global
state itself.
