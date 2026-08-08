<!--
Sync Impact Report
Version change: 1.2.0 → 1.3.0
Modified principles: none
Modified sections:
  - Development Workflow & Quality Gates — added a new requirement that
    every feature's final/Polish phase bump the application version
    (semantic versioning, kept in sync across VERSION,
    frontend/package.json, backend/src/__init__.py) and add a
    corresponding CHANGELOG.md entry describing what shipped, linked to
    that feature's spec. This is a new governance requirement, not a
    redefinition of any existing principle — MINOR bump per the
    versioning policy below.
Added sections: none
Removed sections: none
Follow-up TODOs:
  - TODO(RATIFICATION_DATE): original adoption date unknown; carried over, unrelated to this amendment.
  - Deferred non-governance intents from this amendment are listed under
    "Next Actions" in the command output, not in this file — this command
    does not move or restructure source files.
-->

# PaddockBook Constitution

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)
Tests MUST be written before implementation code for every feature, bug fix, and
API endpoint. The workflow is: write the test, confirm it fails, implement the
minimal code to pass, then refactor (Red-Green-Refactor). No implementation
commit may be made against a requirement that lacks a corresponding failing test
written first. Retrieval logic, department-aware access rules, and financial-data
handling paths are held to this rule without exception, since regressions in
these areas have compliance and confidentiality consequences, not just
functional ones.

### II. Comprehensive Unit Testing
Every unit of business logic — retrieval ranking, document chunking, access
control decisions, request/response transformations — MUST have unit tests that
exercise its success paths, edge cases, and failure modes independently of the
database, network, or LLM provider. Tests that silently depend on live external
services (Postgres, AWS, Anthropic API/Bedrock) are integration tests and MUST be
labeled and isolated as such, not counted as unit coverage. A pull request that
lowers unit test coverage on touched files MUST justify the drop in its
description or be rejected.

### III. API Contract Consistency
The FastAPI backend and Angular frontend communicate through explicit,
versioned contracts (OpenAPI schema generated from FastAPI, consumed by the
Angular client). Any change to a request/response shape, status code, or error
format is a contract change: it MUST be reflected in the schema, MUST NOT break
existing consumers without a version bump, and MUST be accompanied by updated
contract tests. Silent, undocumented API drift between backend and frontend is
prohibited.

### IV. Clean Code & Readability
Code MUST be self-explanatory through naming and structure before it leans on
comments. Functions and classes do one thing; dead code, commented-out blocks,
and speculative abstractions are removed, not left "just in case." Every
module's public surface must be understandable by a reviewer without needing to
read its internals first. Comments are reserved for non-obvious rationale
(a workaround, a regulatory constraint, a subtle invariant) — not for restating
what the code already says.

### V. Separation of Concerns
Retrieval (document indexing/search over Sporting, Technical, and Financial
regulation text), access control (department-aware authorization via
self-hosted authentication — no third-party identity provider), API
orchestration (FastAPI), and presentation (Angular) MUST remain in
distinct, independently testable layers. A layer MUST NOT reach across its
boundary to directly manipulate another layer's internals (e.g., presentation
code MUST NOT embed retrieval or SQL logic; access-control decisions MUST NOT
be duplicated ad hoc inside individual endpoints instead of a shared
authorization layer). This keeps each concern independently verifiable and
prevents confidentiality rules from being bypassed through an untested code
path.

This separation MUST be reflected in the on-disk folder structure of each
codebase, not just enforced through code review discipline:

- **Angular frontend**: `core/` holds singleton services, interceptors, and
  guards; `shared/` holds reusable presentational components with no business
  logic; `features/<name>/` holds one folder per domain, lazy-loaded via the
  router. Every domain-specific feature MUST live under `features/`, never
  directly under `app/`.
- **FastAPI backend**: `modules/<name>/` holds one folder per bounded domain
  (e.g. `health`, `retrieval`, `auth`, `documents`); each module MUST be
  self-contained with its own router, service, schemas, and repository so it
  can be extracted into a standalone service later without restructuring.
  `core/` holds cross-cutting concerns (config, DB session, security,
  middleware) shared across modules.

These conventions exist to support a modular-monolith-now,
decomposable-later architecture: bounded domains stay independently testable
and extractable without a future rewrite of their internal organization.

## Technology & Security Constraints

Stack: FastAPI, Postgres + pgvector, AWS (Lambda/Fargate, CDK), Angular,
Anthropic API/Bedrock. Authentication is self-hosted, not delegated to a
third-party identity provider (e.g. AWS Cognito) — this application owns
credential storage and session/token issuance directly, a deliberate choice
to avoid vendor lock-in on identity. Password credentials MUST be hashed
with a modern adaptive hashing algorithm (e.g. bcrypt or argon2) and MUST
NOT be stored in plaintext or in a reversibly-encrypted form. This is a
private repository containing references to internal financial reporting
processes; nothing derived from this codebase or its regulation corpus may
be made public without explicit review. All access to Sporting, Technical,
and Financial regulation content MUST be mediated by department-aware
authorization checks enforced at the API layer (Principle V) — never solely
in the frontend. Secrets and credentials MUST NOT be committed to the
repository; infrastructure changes (CDK) that alter access permissions or
data exposure MUST be called out explicitly in the PR description.

## Development Workflow & Quality Gates

Every pull request MUST demonstrate: (1) tests written before the
implementation they cover (Principle I), (2) unit test coverage for new or
modified business logic (Principle II), (3) no breaking, undocumented API
contract changes (Principle III), (4) adherence to clean-code review standards
(Principle IV), and (5) respect for existing layer boundaries (Principle V).
Reviewers MUST block merges that violate any of these without an explicit,
documented justification in the PR description. CI MUST run the unit test
suite and MUST fail the build on any regression in previously passing tests.

Every feature's final/Polish phase MUST bump the application version
(`VERSION`, kept in sync with `frontend/package.json` and
`backend/src/__init__.py`) following semantic versioning, and MUST add a
corresponding `CHANGELOG.md` entry — linked to that feature's spec —
describing what shipped. A pull request that completes a feature's Polish
phase without this bump MUST NOT be merged without an explicit, documented
justification in its description.

## Governance

This constitution supersedes ad hoc conventions and prior undocumented
practice for this repository. Amendments require: (1) a documented rationale
for the change, (2) a version bump per the semantic versioning policy below,
and (3) update of any templates or workflows that reference the amended
section. All pull requests and code reviews MUST verify compliance with this
constitution; any added complexity (new layers, new dependencies, deviations
from the stated stack) MUST be justified against these principles in the PR
description.

Versioning policy: MAJOR for backward-incompatible governance changes or
principle removals/redefinitions; MINOR for new principles or materially
expanded guidance; PATCH for clarifications and non-semantic wording fixes.

**Version**: 1.3.0 | **Ratified**: TODO(RATIFICATION_DATE): original adoption date not provided | **Last Amended**: 2026-08-08
