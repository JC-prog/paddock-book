# Phase 0 Research: Local Vector Database for Regulation Chunks

No `NEEDS CLARIFICATION` markers remain in the Technical Context. Both
clarifications from `/speckit-clarify` were resolved in spec.md. This
document records the supporting technical decisions needed to execute the
plan, including two decisions that required live web research since they
depend on current AWS/vendor state rather than fixed project knowledge.

## Decision: pgvector 0.8.1 on PostgreSQL 16, via the `pgvector/pgvector:0.8.1-pg16` image

- **Rationale**: The spec requires the local pgvector version to be
  "consistent with what we'll run on RDS/Aurora later" (FR-009). Checked
  AWS's Aurora PostgreSQL release notes directly (not relying on prior
  knowledge, since this is a fast-moving area): as of this research,
  **pgvector 0.8.1** is the version documented across Aurora PostgreSQL
  16.13, 17.9, and 18.3. The official `pgvector/pgvector` Docker image
  publishes a matching `0.8.1-pg16` tag (confirmed via Docker Hub — pushed
  by the pgvector maintainer, available for both `linux/amd64` and
  `linux/arm64`). PostgreSQL 16 was chosen among the three Aurora-supported
  majors (16/17/18) as the most conservative, broadly-compatible choice.
- **Alternatives considered**: The Docker image's `latest`/unqualified
  `pgvector` tag — currently resolves to pgvector 0.8.6, newer than what
  Aurora actually supports; using it would silently violate FR-009's
  consistency requirement and risk relying on pgvector features not yet
  available on the hosted database. PostgreSQL 17 or 18 — also
  Aurora-supported, but 16 needs no justification for staying conservative
  and matches what a typical production-cautious team would default to
  first.

## Decision: 1024-dimension `vector` column, matching Titan Text Embeddings V2's default

- **Rationale**: Verified directly (not assumed) that Titan Text Embeddings
  V2's `dimensions` parameter defaults to 1024 when unspecified, with 512
  and 256 as smaller opt-in alternatives. This matches the clarification
  answer in spec.md (FR-003) and means a future embedding call that doesn't
  explicitly override `dimensions` will produce vectors that fit the column
  without any coordination required between this feature and that one.
- **Alternatives considered**: 512 or 256 — smaller and faster, but would
  require the future embedding-generation code to explicitly request a
  non-default dimension and would need this schema to change (and existing
  data re-embedded) if that coordination were ever missed. Rejected per the
  clarification's reasoning: retrieval quality favored over storage cost at
  this stage.

## Decision: `documents` and `document_chunks` as two related tables

- **Rationale**: Per the spec.md clarification (FR-004) — a separate
  `documents` table (id, title, created timestamp) referenced by
  `document_chunks` via a foreign key gives document-level metadata a clean
  home and avoids a schema migration later, since no migration tooling
  exists in this project yet (see next decision).
- **Alternatives considered**: A single flat `document_chunks` table with a
  plain text source-identifier column — rejected per the clarification, in
  favor of the lower-migration-risk two-table design.

## Decision: plain SQL init script mounted via Docker's `/docker-entrypoint-initdb.d/`, no migration framework

- **Rationale**: The official Postgres image automatically runs any `.sql`
  file placed in `/docker-entrypoint-initdb.d/` the first time its data
  volume is created — no extra tooling needed for this feature's scope (an
  empty schema with no data to migrate yet). Introducing a framework like
  Alembic now, before any other backend code needs one, would be scope
  creep against Constitution Principle IV (no speculative complexity) — the
  spec's own Assumptions section already calls this out as the intended
  approach.
- **Alternatives considered**: Alembic (or another migration framework) —
  the more scalable long-term choice once real schema evolution and
  production deployments are in play, but unjustified overhead for
  provisioning an empty local schema today. Can be adopted later without
  this feature's SQL script being wasted work (it can seed the framework's
  first migration).

## Decision: no ANN vector index (HNSW/IVFFlat) added in this feature

- **Rationale**: Both pgvector index types are recommended to be built once
  representative data exists — IVFFlat's list-count tuning depends on row
  count, and building either index type against an empty table provides no
  benefit and would need to be reconsidered once a real ingestion pipeline
  (explicitly out of scope here) determines actual data volume and query
  patterns. Adding one now would be speculative (Constitution Principle IV).
- **Alternatives considered**: Adding an HNSW index preemptively — rejected
  as premature; a future retrieval feature is better positioned to choose
  and tune an index once it knows real row counts and query latency
  requirements.

## Decision: `psycopg[binary]` for the schema-verification integration test only

- **Rationale**: The only new Python code this feature adds is a test that
  connects to the running Postgres container and asserts the extension and
  table shapes are correct (Acceptance Scenario 2). `psycopg` (v3) is the
  actively maintained, modern PostgreSQL driver for Python; the `[binary]`
  extra avoids requiring local PostgreSQL build tools. No FastAPI runtime
  code uses this dependency yet — that's for whichever future feature first
  needs to query the database from a request handler.
- **Alternatives considered**: `psycopg2-binary` — the older, still-common
  driver; `psycopg` (v3) was chosen instead since it's the actively
  developed successor and there's no existing codebase convention pulling
  toward v2. `asyncpg` — a valid alternative, but `psycopg` was preferred
  for its more conventional synchronous API, matching the simple, synchronous
  nature of this one verification test.
