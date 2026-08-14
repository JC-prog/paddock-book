# Research: Chat Provider Configuration

## Provider dispatch stays function-based, matching `core/embeddings.py`

**Decision**: `chat/generation.py` gains one public dispatch function
that branches on `provider_config.provider` into three private async
generator functions (`_generate_ollama`, `_generate_bedrock`,
`_generate_openai_compatible`) — plain functions, not a class-based
`LLMProvider` interface/ABC.

**Rationale**: `core/embeddings.py::embed()` already solves the identical
problem (dispatch between Bedrock and Ollama) this exact way, and this
codebase's established DI-via-keyword-defaults test pattern (each
provider function takes an injectable `client_factory`, mirroring
`generate_answer`'s existing `client_factory` parameter) works cleanly
with plain functions. Introducing a class hierarchy here would be the
kind of speculative abstraction Constitution Principle IV calls out —
three known, fixed provider branches don't need polymorphism to add a
fourth later; extending the `if/elif` matches the codebase's own
precedent instead of inventing a second pattern for the same kind of
problem.

**Alternatives considered**: A `Protocol`/ABC-based provider interface
with one class per provider — rejected as unnecessary ceremony for three
fixed branches, and inconsistent with the embeddings module's existing,
working solution to the same shape of problem in the same codebase.

## Bedrock chat uses the Converse API, bridged into an async generator via a background thread

**Decision**: Bedrock chat generation calls `bedrock-runtime`'s
`converse_stream` (not `invoke_model`), and bridges its blocking,
synchronous iterator into this codebase's async-generator streaming
convention by running the iteration in a background thread
(`asyncio.to_thread`) that pushes decoded text deltas onto an
`asyncio.Queue`, consumed by the async generator that `chat/service.py`
already expects.

**Rationale**:

1. **Converse API over `invoke_model`**: `invoke_model`'s request/response
   body shape differs per model family (Anthropic's Messages format,
   Meta's Llama format, Amazon Titan's format, etc.) — supporting an
   admin-entered *arbitrary* Bedrock model identifier (per this feature's
   clarified scope) with `invoke_model` would mean either restricting the
   admin to a hardcoded allow-list of model families or shipping
   per-family request-building logic. Bedrock's Converse API is AWS's own
   unified interface specifically built to give one request/response
   shape across supported model providers, which is exactly what "any
   Bedrock model the admin types in" needs to actually work through one
   code path.
2. **The threading bridge**: `boto3` has no native async client (the
   existing `core/embeddings.py::get_bedrock_client()` is already a
   synchronous `boto3.client(...)`, currently fine because embedding calls
   are quick and non-streaming). Chat generation streams over
   Server-Sent Events for potentially many seconds, so calling a blocking
   `converse_stream` iterator directly inside the FastAPI async event loop
   would stall every other concurrent request for the call's duration.
   `asyncio.to_thread` + a queue is a standard, dependency-free way to
   bridge a blocking iterator into async code without adding a new SDK.

**Alternatives considered**: `aioboto3` (a third-party async wrapper
around boto3) — rejected to avoid adding a whole additional AWS SDK
dependency (with its own version-compatibility surface against the
already-pinned `boto3==1.43.65`) purely to solve one streaming call, when
a standard-library bridge does the same job with zero new dependencies.

## OpenAI-compatible chat uses the official `openai` package's async client

**Decision**: The OpenAI-compatible provider uses `openai.AsyncOpenAI`,
constructed per-request with the admin-saved `base_url` and `api_key`,
calling `chat.completions.create(..., stream=True)`.

**Rationale**: `AsyncOpenAI` already streams natively via Python's async
iteration protocol — the same shape `generate_answer`'s existing
`ollama.AsyncClient` usage has today, so no bridging is needed (unlike
Bedrock). The `base_url` constructor parameter is exactly what makes this
one integration cover "OpenAI itself, Anthropic-compatible proxies, and
other OpenAI-API-compatible services" (spec FR-003/FR-004) without a
vendor-specific SDK per service — any endpoint implementing the
OpenAI chat-completions wire format works, since that's what the
`openai` package's HTTP client actually speaks.

**Alternatives considered**: Hand-rolled `httpx` calls against the
OpenAI-compatible chat-completions endpoint — rejected; the official SDK
already handles request shaping, streaming-chunk parsing, and error
mapping correctly, and this codebase already depends on `httpx`
transitively without needing to hand-build a chat-completions client on
top of it.

## Storage: one singleton table, not split config/credential tables

**Decision**: A single new table, `chat_provider_settings`, one row
(`id = 1`, same constraint pattern as `app_settings`), holding the active
provider selection plus every provider's own settings (Bedrock model,
Ollama override, OpenAI-compatible base URL/key/model) as columns on that
one row.

**Rationale**: The spec's two "entities" (Chat Provider Configuration,
Provider Credential) are both, in practice, exactly-one-row-ever data —
there is one active provider, one Bedrock model, one Ollama override, one
OpenAI-compatible credential, full stop (spec Assumptions: single global
setting, no per-user variation). Splitting that across two tables would
require an always-1:1 join for no benefit; `app_settings` (feature 012)
already established the precedent of one singleton row holding multiple
unrelated settings together in this exact codebase.

**Alternatives considered**: A `provider_credentials` table keyed by
provider name (rows for `bedrock`, `openai_compatible`, etc.) — rejected
as over-general for a fixed, closed set of exactly three providers with
no plan (in this feature's scope) to support user-defined additional
providers; the fixed-column singleton row is simpler to read, write, and
test.

## Cross-module read: `chat/service.py` imports `admin.repository` directly

**Decision**: `chat/service.py` reads the active provider configuration
by importing and calling `admin.repository`'s new
`get_chat_provider_settings(conn)` function directly — not by going
through `admin/service.py`'s business logic layer, and not via a new
shared `core/` module.

**Rationale**: This mirrors an existing, working precedent in this exact
codebase: `modules/jobs/service.py` already imports repository functions
directly from `modules/download/repository.py` and
`modules/ingestion/repository.py` across module boundaries, rather than
going through those modules' service layers or a shared core module.
`admin/service.py`'s logic for this feature is specifically about
*admin-side* mutation validation (FR-012/FR-013's activation-blocking
rules) — reading the current settings for a chat request needs none of
that, just the stored row, so reaching directly into the repository
(read-only) keeps chat's dependency on admin minimal and matches the
codebase's existing "modules read each other's repositories directly, not
each other's business logic" pattern.

**Alternatives considered**: A new `core/chat_provider.py` shared reader —
rejected, since it would duplicate the same table's read logic apart from
`admin/repository.py`'s existing write logic for no clear benefit, and no
other feature in this codebase has needed a "shared core reader for one
module's table" pattern.

## Activation-blocking validation lives in the service layer, not a DB constraint

**Decision**: FR-012 (OpenAI-compatible needs a full credential before
activation) and FR-013 (Bedrock needs a model before activation) are
enforced in `admin/service.py`, raising a dedicated
`IncompleteProviderConfigError`, mapped by `admin/router.py` to
`409 Conflict` — mirroring the existing `DuplicateJobError` → `409` mapping
in `modules/jobs/router.py`.

**Rationale**: `job_runs_active_target_uniq` (feature 013) needed a
genuine DB-level constraint specifically because of a real concurrent-
insert race two simultaneous job triggers could hit. No equivalent race
exists here — this is a single global settings row, updated by one admin
action at a time, and the validation ("is this provider's required data
present") is a straightforward business rule, not a
concurrency-correctness guarantee. `admin/service.py::update_log_destination`
already establishes the pattern of service-layer-enforced rules around
this exact table family; this feature follows that precedent rather than
introducing a DB `CHECK` constraint that can't easily express
"one of three different sets of required-together columns depending on
another column's value."

**Alternatives considered**: A Postgres `CHECK` constraint encoding the
per-provider required-field rules — rejected as significantly harder to
read/maintain than the equivalent Python `if`, for a rule with no
concurrency-safety motivation to justify pushing it into the database.

## API key is never round-tripped — the GET response reports presence, not the value

**Decision**: `GET /v1/admin/settings/chat-provider`'s response includes
`openai_compatible_api_key_set: bool`, never the key itself (FR-011).
`PUT` accepts a **partial update** — any field present in the request
body is changed; any field omitted keeps its previously stored value.
This is what makes FR-015 (switching back to a previously configured
provider doesn't require re-entering its credential) possible: the admin
can `PUT` just `{"active_provider": "bedrock"}` without resending
`openai_compatible_api_key`, and the previously saved key stays intact
untouched, only the active provider column changes.

**Rationale**: A full-replace `PUT` (the more typical REST convention)
would force the frontend to either cache and resend the plain-text key on
every unrelated change (defeating FR-011's "never displayed back"
guarantee — it'd have to have been received back at some point to resend
it) or force re-entry on every save (directly violating FR-015). Partial
update avoids both. This is documented explicitly in
`contracts/admin-api.md` since it's a deliberate deviation from strict
REST `PUT` semantics, not an oversight.

**Alternatives considered**: A strict full-replace `PUT` requiring every
field on every call — rejected for the FR-011/FR-015 conflict above. A
separate `POST /settings/chat-provider/credential` endpoint just for the
API key — rejected as an unnecessary second endpoint when partial-update
semantics on the existing `PUT` cleanly cover the same need with less
surface.
