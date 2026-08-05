# Feature Specification: Local Vector Database for Regulation Chunks

**Feature Branch**: `005-pgvector-local-dev`

**Created**: 2026-08-05

**Status**: Draft

**Input**: User description: "Set up the Postgres + pgvector vector database for regulation document chunks, for local development. Schema: a document_chunks table storing chunk text, its embedding vector, department metadata (Sporting/Technical/Financial — matching the FIA regulation sections), a reference to the source document, and chunk ordering. Embeddings come from AWS Bedrock Titan Text Embeddings V2, so size the vector column accordingly. Local dev environment: a docker-compose.yml running Postgres with the pgvector extension (pinned to a version consistent with what we'll run on RDS/Aurora later), and an .env.example documenting the connection configuration the backend needs. Onboarding script: scripts/dev-setup.sh that bootstraps a new developer's environment — creates the backend .venv and installs dependencies, runs npm install for the frontend, starts the pgvector container via Docker Compose, and scaffolds a local .env from .env.example. Out of scope: PDF parsing, chunking logic, the embedding-generation call, and the ingestion pipeline itself — this feature only provides the storage layer and dev environment they'll depend on."

## Clarifications

### Session 2026-08-05

- Q: What output dimension should the embedding vector column be sized for? → A: 1024 (Titan V2's default/max) — retrieval quality favored over storage cost at this stage, and the path of least surprise for whoever writes the embedding call later.
- Q: Should source documents be their own tracked entity, or just a field on each chunk? → A: Separate `documents` table, referenced by chunks — cheap to add now, avoids a schema migration later once real data exists (no migration tooling exists yet), and gives document-level metadata a clean home.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Provision a local database that mirrors production storage (Priority: P1)

As a backend developer, I want a local database with the vector-search
extension enabled and the regulation-chunk schema already provisioned, so
that I can build and test retrieval and ingestion logic against a real
database that mirrors what will run in the hosted environment later.

**Why this priority**: Nothing that depends on storing or querying
regulation chunks (chunking, embedding generation, retrieval — all future
work) can be built or tested locally until this storage layer exists. This
is the foundation everything else in the RAG pipeline sits on.

**Independent Test**: Start the local database and confirm the chunk-storage
table exists with the expected columns and that the vector-search extension
is enabled — fully verifiable with no application code, just inspecting the
running database.

**Acceptance Scenarios**:

1. **Given** Docker is available, **When** a developer starts the local
   database, **Then** a Postgres instance with the vector-search extension
   enabled comes up and is reachable.
2. **Given** the local database is running, **When** a developer inspects
   it, **Then** a chunk-storage table exists with columns for chunk text, an
   embedding vector, a department (Sporting, Technical, or Financial), a
   reference to the source document, and the chunk's order within that
   document.
3. **Given** the local database already has stored data, **When** a
   developer stops and restarts the database, **Then** the previously
   stored data is still there.
4. **Given** a developer wants to connect the backend to this database,
   **When** they look at the environment configuration example, **Then**
   every connection setting the backend needs is documented there with
   safe, non-secret local-development values.

---

### User Story 2 - Bootstrap a new developer's entire local environment in one step (Priority: P2)

As a new developer joining PaddockBook, I want a single script that sets up
my whole local environment — backend dependencies, frontend dependencies,
the local database, and my own environment configuration — so that I can go
from a fresh clone to a working setup without hunting through multiple docs
for manual steps.

**Why this priority**: A meaningful convenience and onboarding-speed
improvement, but the project remains usable via existing manual steps
without it. The database itself (User Story 1) is the harder dependency
other work actually blocks on.

**Independent Test**: On a machine with only the prerequisites installed
(a supported Python version, Node.js, and Docker), run the onboarding
script from a fresh clone and confirm it finishes with a working backend
environment, installed frontend dependencies, a running database, and a
populated local environment file — fully verifiable without manually
running any of the individual setup steps.

**Acceptance Scenarios**:

1. **Given** a fresh clone with no backend virtual environment yet,
   **When** the onboarding script runs, **Then** a backend virtual
   environment is created and its dependencies are installed.
2. **Given** a fresh clone with no frontend dependencies installed,
   **When** the onboarding script runs, **Then** frontend dependencies are
   installed.
3. **Given** the local database is not yet running, **When** the onboarding
   script runs, **Then** the local database starts.
4. **Given** no local environment file exists yet, **When** the onboarding
   script runs, **Then** one is created from the example file.
5. **Given** a developer re-runs the onboarding script on a machine that is
   already set up, **When** it runs again, **Then** it completes without
   destroying or overwriting existing work (e.g. a developer's already-
   customized environment file is left untouched, and the script does not
   error out just because setup was already done).

---

### Edge Cases

- What happens when Docker isn't installed or isn't running when a
  developer tries to start the local database? The failure must be clear
  and actionable, not a cryptic error.
- What happens when a developer already has a customized local environment
  file? The onboarding script must never silently overwrite it.
- What happens when the local database's port is already in use by
  something else on the developer's machine (e.g. another local Postgres)?
  Startup must fail clearly rather than silently connecting to the wrong
  database.
- What happens if a future embedding call returns a vector of a different
  size than the column expects? Out of scope to validate here — no
  embedding-generation code exists yet — but the column must be sized
  correctly from the start per FR-003 so this doesn't surface later.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a local database with a vector-search
  extension enabled, startable with a single command.
- **FR-002**: The local database MUST persist stored data across restarts
  of the database process/container — data MUST NOT be wiped just because
  the database was stopped and started again.
- **FR-003**: The system MUST provision a chunk-storage table with columns
  for: chunk text content, an embedding vector sized for AWS Bedrock Titan
  Text Embeddings V2's 1024-dimensional output, a department value
  restricted to Sporting, Technical, or Financial, a reference to the
  source document, and the chunk's order within that document.
- **FR-004**: The system MUST track source documents as their own entity
  (not just a loose identifier field on each chunk), so that each document
  chunk references a specific tracked source document.
- **FR-005**: The system MUST document every connection setting the backend
  needs to reach the local database, in a version-controlled example file
  with safe, non-secret local-development default values.
- **FR-006**: The system MUST provide a single onboarding script that: sets
  up the backend's Python environment (creating a virtual environment and
  installing dependencies), installs frontend dependencies, starts the
  local database, and creates a local environment file from the example
  file if one does not already exist.
- **FR-007**: The onboarding script MUST NOT overwrite an existing local
  environment file.
- **FR-008**: The onboarding script MUST be safe to re-run on a machine
  that has already been set up, without erroring or destroying existing
  work.
- **FR-009**: The vector-search extension version used locally MUST be
  documented and chosen for consistency with what the team intends to run
  in the eventual hosted database environment.

### Key Entities

- **Document Chunk**: A single stored segment of a source regulation
  document. Attributes: chunk text, embedding vector (1024-dimensional),
  department (Sporting, Technical, or Financial), a reference to its source
  document, and its order within that document.
- **Source Document**: A tracked regulation document that chunks belong to.
  Attributes: an identifier and enough descriptive metadata (e.g. a title)
  to distinguish one source document from another. A single source document
  has many document chunks. No source documents or chunks are created by
  this feature — it only provisions the empty structure that a future
  ingestion feature will populate.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer with Docker installed can go from a fresh clone
  to a running, schema-provisioned local database in under 5 minutes using
  a single command.
- **SC-002**: 100% of the connection settings the backend needs to reach
  the local database are present in the example environment file, verified
  by successfully connecting using only values derived from it.
- **SC-003**: Restarting the local database preserves 100% of previously
  stored data, verified through manual testing.
- **SC-004**: A brand-new developer machine can go from a fresh clone to a
  fully working local environment (backend, frontend, database, and
  environment file all in place) via a single onboarding script run,
  verified by successfully starting both the backend and frontend
  afterward.
- **SC-005**: Re-running the onboarding script on an already-set-up machine
  completes without data loss or errors, verified through testing.

## Assumptions

- PDF parsing, chunk-splitting logic, calling Bedrock to generate
  embeddings, and any pipeline that actually populates the chunk-storage
  table are explicitly out of scope for this feature, per the input
  description — this feature only provisions the empty schema and local
  environment they will depend on.
- The specific vector-search extension version to pin locally (for
  consistency with the eventual hosted database) is a research question for
  planning, not a scope decision — it will be resolved by checking current
  hosted-database compatibility at implementation time rather than fixed
  here.
- No database migration framework exists in the backend yet; schema
  provisioning for this feature uses a plain initialization script rather
  than introducing a migration tool, since no ORM or migration tooling is
  part of the project today. This can be revisited if one is adopted later.
- Local database credentials in the example environment file are
  placeholder, development-only values — never real secrets — consistent
  with that file being safe to commit to the repository.
- Chunk ordering is a simple sequential position per source document,
  sufficient for reconstructing chunk sequence; no hierarchical or
  section-based numbering scheme is required at this stage.
- This feature does not include any UI or API endpoint — it is purely the
  database schema, local dev environment, and onboarding script.
