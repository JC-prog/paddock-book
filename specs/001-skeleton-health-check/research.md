# Phase 0 Research: Foundational Application Skeleton with Health Check

No `NEEDS CLARIFICATION` markers remain in the Technical Context — the stack was
specified directly by the user (FastAPI backend, Angular frontend) and the spec's
`/speckit-clarify` pass resolved the one open question (response-time threshold). This
document records the supporting technology decisions made to fill in the plan.

## Decision: Backend framework — FastAPI + Uvicorn

- **Rationale**: Specified directly by the user and matches the stack already declared
  in the project README (FastAPI, Postgres + pgvector, AWS, Angular, Anthropic
  API/Bedrock). FastAPI generates an OpenAPI schema automatically, which directly
  supports Constitution Principle III (API Contract Consistency).
- **Alternatives considered**: Flask (no built-in OpenAPI generation, weaker async
  support), Django (far heavier than needed for a liveness-only skeleton).

## Decision: Frontend framework — Angular (CLI-scaffolded)

- **Rationale**: Specified directly by the user and matches the README's declared
  stack. Angular's CLI provides `HttpClientTestingModule`, which supports unit-testing
  the health check call without a live backend (Constitution Principle II).
- **Alternatives considered**: None — framework was a hard input, not a choice point.

## Decision: Backend testing — pytest + FastAPI `TestClient`

- **Rationale**: `TestClient` (built on `httpx`) lets the `/health` route be tested
  in-process without starting a real server or touching the network, keeping the test a
  true unit test per Constitution Principle II. pytest is the de facto standard for
  Python FastAPI projects.
- **Alternatives considered**: `unittest` (more boilerplate, no fixture ecosystem);
  hitting a running server over HTTP in tests (turns a unit test into an integration
  test, against Principle II).

## Decision: Frontend testing — Jasmine/Karma (Angular CLI default) with `HttpClientTestingModule`

- **Rationale**: Ships by default with `ng generate`, requires no extra tooling setup
  for a foundational skeleton, and `HttpClientTestingModule` lets the health service be
  tested against a mocked HTTP backend — covering the healthy, unreachable, and
  in-progress states from FR-004 without a real backend process running.
- **Alternatives considered**: Jest (faster, popular alternative, but adds a
  non-default tooling dependency for no functional benefit at this stage — can be
  revisited later without affecting this feature's scope).

## Decision: Cross-origin access from the Angular dev server to the FastAPI backend

- **Rationale**: The Angular dev server (typically `localhost:4200`) and the FastAPI
  backend (typically `localhost:8000`) run as separate local processes, so the backend
  must send permissive CORS headers for local-development origins on the `/health`
  route. This is a local-dev-only concern; production origin policy is out of scope
  (per spec Assumptions: local development only).
- **Alternatives considered**: Angular CLI dev-server proxy (`proxy.conf.json`) to avoid
  CORS entirely — viable and simpler for local dev; left as an implementation-time
  choice between the two since both satisfy FR-003 identically from the frontend's
  perspective. Documented here so the task list can pick one without re-litigating it.

## Decision: Health response shape

- **Rationale**: A minimal JSON body — a `status` field with value `"ok"` — is
  sufficient to satisfy FR-001 (report operational) and FR-004 (frontend can render
  healthy vs. not). No version/uptime/dependency fields are needed since dependency
  checks are explicitly out of scope (spec Assumptions).
- **Alternatives considered**: Richer payload (uptime, version, dependency statuses) —
  rejected as premature; nothing in the spec calls for it and it would need its own
  tests/contract for fields no requirement uses.
