# Implementation Plan: Chat Provider Configuration

**Branch**: `016-chat-provider-config` | **Date**: 2026-08-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-chat-provider-config/spec.md`

## Summary

Add an admin-only settings page that lets an operator choose which LLM
provider powers chat answer generation — Ollama (existing, zero-config),
AWS Bedrock (an admin-entered model identifier; AWS credentials remain
externally managed, unchanged), or a generic OpenAI-API-compatible
connection (an admin-entered base URL, API key, and model name, covering
OpenAI itself and any OpenAI-compatible service through one integration)
— and have that choice take effect for the very next chat request with no
deploy or restart. `chat/generation.py`, currently hardcoded to a single
Ollama call, becomes a three-way dispatch read from a new singleton
database row each request, following the same function-dispatch pattern
`core/embeddings.py` already uses for its own Bedrock/Ollama switch. The
admin settings module (`modules/admin/`) gains the new table's CRUD,
mirroring its existing `log_to_file` singleton-setting pattern exactly.

## Technical Context

**Language/Version**: Python 3.11 (FastAPI backend), TypeScript (Angular
19 frontend) — existing stack, unchanged.

**Primary Dependencies**: FastAPI, psycopg3, boto3 (already a dependency,
used today only for Bedrock *embeddings*; this feature adds its first
Bedrock *chat* usage via the Converse API), `ollama` SDK (existing), and a
new dependency — the official `openai` Python package, used purely as an
HTTP client against an admin-supplied `base_url` (not necessarily
OpenAI's own endpoint) for the OpenAI-compatible provider.

**Storage**: PostgreSQL — one new singleton table, `chat_provider_settings`
(same one-row pattern as the existing `app_settings` table from feature
012), holding the active provider plus every provider's saved settings.

**Testing**: pytest — unit tests for `generation.py`'s three provider
branches (mocked clients, no live network/AWS calls) and `admin`
module's new service/repository logic; integration tests (real Postgres)
for the new repository functions and migration, matching this project's
existing unit/integration split (Constitution Principle II).

**Target Platform**: Linux server (existing Docker/Fargate-oriented
deployment target).

**Project Type**: Web application (FastAPI backend + Angular frontend) —
existing `backend/` + `frontend/` structure, no new top-level project.

**Performance Goals**: The active provider config is read fresh from the
database on every chat request (no in-process caching) — this is what
makes SC-001 ("takes effect on the very next request, no restart") true
by construction. A single-row primary-key lookup adds negligible latency
next to an LLM generation call.

**Constraints**: No live provider/model validation at save time (spec
Assumptions — errors surface only when a real chat request is attempted).
The saved API key is stored as plain text (spec FR-010, an explicit,
documented tradeoff, not an oversight). `boto3` has no native async
client, so Bedrock's streaming Converse API call must be bridged onto
this codebase's existing async-generator streaming convention without
blocking the FastAPI event loop (see research.md).

**Scale/Scope**: One global configuration row; three provider code paths;
no per-user or per-conversation variation (spec Assumptions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Test-First, NON-NEGOTIABLE)**: tasks.md will sequence a
  failing test before every implementation task, for both the new
  `admin` repository/service/router logic and `generation.py`'s new
  provider branches. PASS.
- **Principle II (Comprehensive Unit Testing)**: `generation.py`'s three
  provider functions are unit-tested with mocked clients (`client_factory`
  DI, matching the existing Ollama test's pattern) — no real network/AWS
  calls in unit tests. Any test touching Postgres lives under
  `tests/integration/`, matching `test_admin_repository.py`'s existing
  placement. PASS.
- **Principle III (API Contract Consistency)**: New
  `GET`/`PUT /v1/admin/settings/chat-provider` endpoints are documented in
  `contracts/admin-api.md` before implementation; the existing
  `POST /v1/chat` request/response shape is unchanged (this feature only
  changes what happens *inside* that handler, not its wire contract), so
  no contract change is needed there. PASS.
- **Principle IV (Clean Code)**: The three provider implementations
  (`_generate_ollama`, `_generate_bedrock`, `_generate_openai_compatible`)
  are plain, independently readable functions behind one dispatch
  function — no premature interface/class abstraction, matching
  `core/embeddings.py`'s existing two-provider dispatch precedent exactly
  (now extended to three). PASS.
- **Principle V (Separation of Concerns)**: `admin/` owns the new table's
  CRUD and activation-validation business rule; `chat/generation.py`
  stays a pure LLM-calling layer that receives an already-resolved
  provider configuration and has no DB dependency of its own;
  `chat/service.py` reads the active configuration by importing
  `admin.repository` directly — an established cross-module pattern
  already used by `modules/jobs/service.py` (which imports repository
  functions from both `modules/download/repository.py` and
  `modules/ingestion/repository.py`), not a new precedent. PASS.

No violations requiring justification — Complexity Tracking is empty.

**Post-Phase 1 re-check**: `research.md` and `data-model.md` confirm the
above holds with no surprises — the singleton-table storage decision,
the service-layer (not DB-constraint) activation validation, and the
direct cross-module repository read all follow existing precedent in
this codebase rather than introducing new patterns. Still PASS on all
five principles.

## Project Structure

### Documentation (this feature)

```text
specs/016-chat-provider-config/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── admin-api.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── modules/
│   │   ├── admin/
│   │   │   ├── router.py       # + GET/PUT /v1/admin/settings/chat-provider
│   │   │   ├── service.py      # + get/update_chat_provider_config, activation validation
│   │   │   ├── repository.py   # + get/set_chat_provider_settings
│   │   │   └── schemas.py      # + ChatProviderSettings request/response models
│   │   └── chat/
│   │       ├── generation.py   # rewritten: 3-way provider dispatch (was Ollama-only)
│   │       └── service.py      # generate_reply() reads active config via admin.repository
│   └── core/
│       └── ...                 # unchanged
├── tests/
│   ├── unit/
│   │   ├── test_admin_service.py     # + activation-validation tests
│   │   ├── test_admin_router.py      # + new endpoint tests
│   │   └── test_chat_generation.py   # + Bedrock/OpenAI-compatible branch tests
│   └── integration/
│       └── test_admin_repository.py  # + chat_provider_settings CRUD tests
└── requirements.txt      # + openai

db/init/
└── 005_chat_provider_config.sql   # new singleton table (see data-model.md)

frontend/
└── src/app/
    ├── app.routes.ts                          # + /admin/chat-provider route
    └── features/admin/chat-provider/
        └── chat-provider.component.ts         # new page, mirrors admin.component.ts's
                                                 # signals + inline-HttpClient pattern
```

**Structure Decision**: Extends the existing `backend/` (FastAPI) +
`frontend/` (Angular) web-application structure — no new top-level
project. The feature lives inside the existing `admin` bounded domain
(new table, new endpoints, alongside the existing `log_to_file` setting)
plus a targeted rewrite of `chat/generation.py`'s single hardcoded
provider call into a three-way dispatch; both are extensions of existing
modules, not new ones, per Constitution Principle V's
one-folder-per-bounded-domain structure.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
