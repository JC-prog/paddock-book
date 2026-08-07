# Phase 0 Research: Retrieval-Grounded Chat Answers

No `NEEDS CLARIFICATION` markers remain in the Technical Context. `/speckit-clarify`
found no unresolved ambiguities in spec.md. This document records the supporting
technical decisions needed to execute the plan.

## Decision: `ollama` 0.6.2 Python client for local generation, with a
Bedrock swap deferred to production

- **Rationale**: The user explicitly chose to prototype against a local Ollama
  instance and swap to AWS Bedrock in production, rather than build both now.
  The official `ollama` package (MIT license, verified current on PyPI) wraps
  Ollama's REST API with sync and async clients; the async client is used here
  so `generation.py`'s call doesn't block the event loop, matching the
  `async def` pattern the existing `/v1/chat` router already uses (feature
  003). `generation.py`'s public surface is a single function that takes a
  prompt/context and yields tokens — the same shape a future
  `core/generation.py` Bedrock implementation would expose, so swapping
  providers later is a scoped, single-module change, not a rewrite of
  `service.py`/`router.py`.
- **Alternatives considered**: Building the Bedrock path now too, behind a
  provider flag — rejected as speculative (Constitution Principle IV); nothing
  today needs it, and building an untested, unused code path is worse than a
  clean single-provider implementation with an intentionally narrow
  integration point. `langchain`/`llama-index` or similar orchestration
  frameworks — rejected as unjustified weight for what's a single retrieval
  query and a single chat-completion call; this project has consistently
  avoided heavier frameworks (e.g. `argparse` over `click` in feature 006) in
  favor of direct, minimal code for a small integration surface.

## Decision: `llama3.2` as the default local Ollama model, configurable

- **Rationale**: A small, modern, widely-used general-purpose model that runs
  reasonably on typical developer hardware — appropriate for a prototyping
  target where the point is proving the retrieval-and-generation flow works,
  not model quality tuning. Exposed as `Settings.ollama_model` (default
  `"llama3.2"`) so it's a one-line change to try a different local model
  without touching code.
- **Alternatives considered**: Pinning a specific model as a hard constant
  with no setting — rejected; since this is explicitly a prototyping target
  that will be replaced in production anyway, making the local model
  effortless to swap costs nothing and avoids a rebuild for a one-line change.

## Decision: promote the Bedrock embedding call to `core/embeddings.py`

- **Rationale**: `modules/ingestion/embeddings.py` (feature 006) already calls
  Bedrock's Titan V2 `InvokeModel` to embed chunk text. This feature needs the
  identical call to embed a user's question, since pgvector similarity is only
  meaningful when the query vector and the stored vectors come from the same
  model. Rather than duplicate the `boto3` client setup and `InvokeModel`
  payload shape a second time inside `modules/chat/`, the shared logic moves
  to `core/embeddings.py` (`get_bedrock_client`, `embed_text`), and
  `modules/ingestion/embeddings.py`'s `embed_chunk` becomes a thin wrapper
  around it — its public signature and `EmbeddedChunk` dataclass are
  unchanged, so feature 006's existing tests keep passing with only their
  import path updated. This is the same "second real consumer" trigger the
  constitution already used to justify `core/config.py` (ingestion) and
  `core/security.py` (auth) — not a speculative extraction ahead of a real
  need.
- **Alternatives considered**: Having `modules/chat/retrieval.py` import
  directly from `modules/ingestion/embeddings.py` — rejected; a module
  reaching into another module's internals is exactly what Constitution
  Principle V's "each module self-contained, extractable into a standalone
  service" guarantee exists to prevent. Duplicating the ~15 lines of
  boto3/InvokeModel code in `modules/chat/` instead — rejected as needless
  duplication of logic that must stay in sync (model ID, dimensions, request
  shape) between two copies.

## Decision: pgvector cosine-distance query, `ORDER BY embedding <=> query LIMIT 5`, no distance threshold cutoff

- **Rationale**: `<=>` is pgvector's cosine-distance operator; sorting
  ascending by it and taking the closest 5 chunks is the standard retrieval
  query pattern, consistent with feature 005's decision not to add an
  ANN index yet (the corpus is small enough that a sequential scan is fine).
  A hard distance-threshold cutoff (excluding chunks "too far" from the
  query) was considered but not adopted for v1: picking a numerically correct
  threshold requires empirical tuning against Titan V2's actual embedding
  space that isn't available yet, and an arbitrary guessed threshold risks
  being worse than no threshold at all. Instead: (a) if literally zero chunks
  exist for the requester's department (empty corpus), the "no relevant
  information" response is returned deterministically without ever calling
  the LLM; (b) when chunks ARE retrieved but don't actually answer the
  question, the generation prompt explicitly instructs the model to say so
  rather than guess. This second case is a known, honestly-documented
  limitation given guardrails (which would otherwise add a second, more
  reliable enforcement layer) are explicitly out of scope for this feature —
  SC-002's "zero fabricated details" guarantee is deterministic only for the
  empty-corpus case; the "irrelevant-but-retrieved" case relies on prompt
  instruction-following, which is inherently imperfect.
- **Alternatives considered**: A hard distance threshold anyway with a
  best-guess value — rejected per above, an uncalibrated number is false
  precision, not a real safeguard. Deferring the empty-corpus short-circuit
  too (always calling the LLM) — rejected; it's a free, deterministic
  improvement over relying on the model alone, with no real cost.

## Decision: `POST /v1/chat` gains `Depends(get_current_user)`; no new auth code

- **Rationale**: Feature 007 built `get_current_user` in `core/security.py`
  specifically as "a reusable request-authentication mechanism a future
  feature can apply" (feature 007 spec.md Assumptions) to existing endpoints.
  This is that future feature. Adding the dependency to the router function
  signature both rejects unauthenticated requests (FR-001) and gives the
  handler the requester's `department` claim directly from the validated JWT
  — no extra database round-trip needed to look up the user's department for
  the retrieval filter.
- **Alternatives considered**: None seriously — this is exactly the
  documented purpose of the existing dependency; building a second
  auth-checking mechanism would duplicate feature 007 for no reason.

## Decision: preserve SSE streaming; stream real generated tokens instead of the fixed placeholder's words

- **Rationale**: The existing frontend (`chat-api.service.ts`, feature 004)
  already parses an SSE stream of `data:` lines word-by-word. Ollama's chat
  API supports streaming (`stream=True`), yielding successive response
  fragments — wiring `generation.py` as an async generator that yields those
  fragments keeps the existing `EventSourceResponse` wiring in `router.py`
  and the entire frontend parsing/rendering path unchanged, just fed by real
  content instead of a fixed string split on spaces.
- **Alternatives considered**: Switching to a single blocking JSON response
  — rejected; it would require rewriting the frontend's SSE-based rendering
  logic (feature 004) for no benefit, and loses the "answer appears
  progressively" UX the placeholder already established.

## Decision: frontend attaches the access token by adding an `Authorization`
header to the existing `fetch` call, not by migrating to `HttpClient`

- **Rationale**: `chat-api.service.ts` uses raw `fetch` (not Angular's
  `HttpClient`) specifically for its streaming `ReadableStream` handling
  (feature 003/004 research). Feature 007's `authInterceptor` only attaches
  to `HttpClient` requests, so it doesn't apply here automatically — the
  fetch call needs the header added explicitly, reading the token from
  `AuthService.getAccessToken()` (feature 007). This is a small, targeted
  change to one existing call site, not a rewrite of the streaming logic.
- **Alternatives considered**: Migrating `chat-api.service.ts` to
  `HttpClient` so the existing interceptor "just works" — rejected;
  `HttpClient` doesn't provide the same raw `ReadableStream`
  reader access feature 003/004 already deliberately chose `fetch` for, so
  this would risk destabilizing already-working, already-tested streaming
  code for a marginal DRY benefit.
