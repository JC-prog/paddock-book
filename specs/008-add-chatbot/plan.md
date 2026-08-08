# Implementation Plan: Retrieval-Grounded Chat Answers

**Branch**: `feat/008-add-chatbot` | **Date**: 2026-08-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-add-chatbot/spec.md`

## Summary

Replace `POST /v1/chat`'s fixed placeholder reply with a real, retrieval-grounded
answer: the request now requires a logged-in staff member (reusing feature 007's
`get_current_user`), embeds their question with the same model used to embed the
ingested regulation chunks (feature 006's Titan V2), retrieves the closest chunks
filtered to the requester's department, and streams a generated answer from a
local Ollama model — grounded in that retrieved text, or an explicit "no relevant
information" reply when nothing useful was retrieved. Guardrails against
adversarial prompt manipulation are explicitly out of scope (spec.md Assumptions);
the production LLM provider (Bedrock) is a documented future swap, not built here.

## Technical Context

**Language/Version**: Python 3.12 (backend, unchanged); TypeScript 5.x / Angular
18 (frontend, unchanged)

**Primary Dependencies**: `ollama` 0.6.2 (official Python client for local Ollama
chat generation — MIT license; provides both a sync and async client, the latter
used here so the existing SSE streaming pattern from feature 003 isn't blocked by
a synchronous call); `boto3`/`psycopg`/`sse-starlette` (existing). No new frontend
dependency — `chat-api.service.ts`'s existing fetch-based SSE parsing (feature
004) is reused as-is, with an added `Authorization` header.

**Storage**: PostgreSQL + pgvector (existing, features 005/006) — this feature
only reads `document_chunks` (cosine-distance `ORDER BY ... LIMIT` query); no new
tables, no schema change.

**Testing**: pytest. `retrieval` needs a real Postgres and a real pgvector query,
so it lives in `tests/integration/`, matching the Constitution Principle II
distinction established since feature 005. `generation` is unit-tested against a
mocked Ollama client (no real model call), matching how feature 006 unit-tested
the Bedrock embedding call. `service` is unit-tested with all collaborators
mocked. Vitest for `chat-api.service.ts`'s auth-header attachment.

**Target Platform**: Local dev (a locally-running Ollama instance); production
uses a different LLM provider (Bedrock) per an explicit user decision — not built
in this feature (spec.md Assumptions).

**Project Type**: Web application (backend + frontend) — extends the existing
`modules/chat/`/`features/chat/` from features 003/004.

**Performance Goals**: Not a hard numeric target — spec's SC-006 asks for a
"short, predictable wait" with a clear failure indication, not a specific
latency bound.

**Constraints**: Chat now requires authentication (FR-001) — reuses feature
007's `get_current_user` dependency rather than building new auth logic;
retrieval MUST be filtered to the requesting user's department (FR-003),
enforced via a `WHERE department = %s` clause using the department claim
already embedded in the JWT (no extra DB lookup needed); the question's
embedding MUST use the same model/dimensions as the stored chunk embeddings
(Titan V2, 1024-dim, feature 006) since pgvector similarity is only meaningful
within one embedding space — this holds regardless of which model generates the
final answer.

**Scale/Scope**: `modules/chat/` gains `retrieval.py` and `generation.py`;
`service.py`/`router.py` are modified. The Bedrock embedding call is promoted
from `modules/ingestion/embeddings.py` into a new `core/embeddings.py`, since
this feature is the second real consumer of "embed this text via Titan V2" —
the same promotion trigger the constitution used for `core/config.py` and
`core/security.py`. One frontend file (`chat-api.service.ts`) is modified.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature | Status |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Yes — failing tests for `retrieval` (integration), `generation` (mocked), `service` (mocked), and the updated `router`/contract behavior must exist before their implementations | PASS (enforced at task-generation/implementation time) |
| II. Comprehensive Unit Testing | Yes — `generation`/`service` are true unit tests with no live dependency (Ollama is mocked); `retrieval` correctly lives in `tests/integration/` since it needs a real Postgres+pgvector, matching the established distinction | PASS |
| III. API Contract Consistency | Yes — `POST /v1/chat`'s contract changes materially (now requires auth; response content is generated, not fixed); `contracts/chat-api.md` (originally written for feature 003) is updated to match, kept in sync with `tests/unit/test_chat.py` | PASS |
| IV. Clean Code & Readability | Yes — the `core/embeddings.py` promotion is a justified refactor with a concrete second consumer (this feature), not speculative; no distance-threshold engineering beyond what's needed for the deterministic "corpus is empty" case (research.md) | PASS |
| V. Separation of Concerns | Yes — retrieval/generation stay inside `modules/chat/`; the shared Bedrock embedding call moves to `core/`, matching how `core/security.py` became the shared home for JWT logic once a second module needed it; frontend change stays inside `features/chat/` | PASS |

No violations. Complexity Tracking is not needed.

**Post-Phase 1 re-check**: research.md, data-model.md, contracts/chat-api.md,
and quickstart.md introduce no new dependency, module, or pattern beyond what
Technical Context and the table above already accounted for. The
`core/embeddings.py` promotion and the reuse of feature 007's
`get_current_user` are both justified by a concrete second consumer, not
speculative extraction — Principle IV in action, not tension with it. The
deliberate choice not to add an uncalibrated distance-threshold cutoff
(research.md) is the same discipline. All 5 principles remain PASS.

## Project Structure

### Documentation (this feature)

```text
specs/008-add-chatbot/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── requirements.txt                  # modified — add `ollama`
└── src/
    ├── core/
    │   ├── config.py                   # modified — add ollama_model, ollama_host settings
    │   └── embeddings.py                # new — promoted from modules/ingestion/embeddings.py:
    │                                     #        get_bedrock_client, embed_text (Titan V2 call)
    └── modules/
        ├── ingestion/
        │   └── embeddings.py             # modified — embed_chunk() now delegates to
        │                                  #            core.embeddings.embed_text(); public
        │                                  #            behavior/tests unchanged
        └── chat/
            ├── retrieval.py               # new — embeds the question, queries pgvector
            │                               #       filtered by department
            ├── generation.py               # new — Ollama chat call (streaming), prompt
            │                                #       construction, "no relevant info" fallback
            ├── service.py                   # modified — orchestrates retrieval → generation,
            │                                 #            replaces generate_placeholder_reply
            ├── router.py                     # modified — POST /v1/chat now requires
            │                                  #            Depends(get_current_user) (feature 007)
            └── schemas.py                     # unchanged — ChatRequest already fits

backend/tests/
├── unit/
│   ├── test_chat.py                   # modified — updated for auth-required, generated
│   │                                    #            (not fixed) responses
│   ├── test_chat_generation.py          # new — mocked Ollama client
│   ├── test_chat_service.py              # new — mocked retrieval/generation collaborators
│   └── test_ingestion_embeddings.py       # modified — imports EMBEDDING_MODEL_ID/
│                                            #            EMBEDDING_DIMENSIONS from their new
│                                            #            home (core.embeddings); behavior
│                                            #            assertions unchanged
└── integration/
    └── test_chat_retrieval.py            # new — real Postgres + pgvector required

frontend/src/app/features/chat/
└── chat-api.service.ts                 # modified — attaches the access token
                                          #            (AuthService, feature 007) to the request
```

**Structure Decision**: `modules/chat/` keeps its existing router/service/
schemas shape (feature 003's precedent) and gains `retrieval.py`/`generation.py`
as new single-purpose collaborators, mirroring how `modules/ingestion/` split
`parser`/`chunker`/`embeddings`/`repository` into independently-testable pieces.
The Bedrock embedding call moves to `core/embeddings.py` because this feature
is a second real consumer of it — the same "core/ gets its first/next real use"
reasoning already used for `core/config.py` (ingestion) and `core/security.py`
(auth). `modules/ingestion/embeddings.py` keeps its own public surface
(`EmbeddedChunk`, `embed_chunk`) but delegates the actual API call, so feature
006 is unaffected behaviorally. Auth is enforced by depending on feature 007's
already-built, already-tested `get_current_user` — no new auth logic is written
here. The frontend change is intentionally minimal: `chat-api.service.ts`'s
existing fetch-based SSE parsing (feature 004) is untouched except for adding
the `Authorization` header, so the streaming UX doesn't need to be rebuilt.

## Complexity Tracking

*Not applicable — the Constitution Check above has no violations to justify.*