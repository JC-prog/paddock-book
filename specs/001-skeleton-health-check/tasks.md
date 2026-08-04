---

description: "Task list for Foundational Application Skeleton with Health Check"
---

# Tasks: Foundational Application Skeleton with Health Check

**Input**: Design documents from `/specs/001-skeleton-health-check/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/health-api.yaml, quickstart.md

**Tests**: Included and required — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates a failing test before implementation for every requirement in this feature.

**Organization**: This feature has a single user story (P1). Tasks are grouped by phase; all user-facing implementation tasks carry the `[US1]` label.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 — the only story in this feature)
- Paths below follow the Option 2 (web app) structure from plan.md: `backend/src/`, `backend/tests/`, `frontend/src/app/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create backend directory structure (`backend/src/`, `backend/src/api/`, `backend/tests/unit/`) per plan.md Project Structure
- [X] T002 Initialize Python backend project with FastAPI, Uvicorn, pytest, and httpx dependencies in `backend/requirements.txt`
- [X] T003 [P] Scaffold Angular frontend application in `frontend/` via Angular CLI (`ng new`) per plan.md Project Structure

**Checkpoint**: Both `backend/` and `frontend/` exist as installable projects.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared app scaffolding that the health-check story is built on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create FastAPI app instance with CORS middleware enabled for the local Angular dev-server origin in `backend/src/main.py`
- [X] T005 [P] Configure Angular `HttpClient` provider in `frontend/src/app/app.config.ts`
- [X] T006 [P] Create base Angular app shell (no health logic yet) in `frontend/src/app/app.component.ts`

**Checkpoint**: Foundation ready — backend app object and frontend shell both exist and run, but expose no functionality yet.

---

## Phase 3: User Story 1 - Confirm the application is wired together end-to-end (Priority: P1) 🎯 MVP

**Goal**: A backend service and a frontend application that talks to it, so a developer can confirm the two halves of the system communicate before any real feature work begins.

**Independent Test**: Start the backend, start the frontend, open the frontend in a browser, and observe a visible confirmation that it successfully reached the backend (per spec.md Acceptance Scenarios 1–3).

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (Constitution Principle I)**

- [X] T007 [P] [US1] Write failing backend tests for `GET /health` — status code, response body matches `contracts/health-api.yaml`, response time under 500ms (FR-001, FR-005, SC-004) in `backend/tests/unit/test_health.py`
- [X] T008 [P] [US1] Write failing tests for `HealthService` covering healthy, unreachable, and in-progress responses using `HttpClientTestingModule` (FR-003) in `frontend/src/app/health/health.service.spec.ts`
- [X] T009 [P] [US1] Write failing tests for `HealthStatusComponent` rendering the three required states — healthy, unreachable, checking (FR-004) in `frontend/src/app/health/health-status.component.spec.ts`

### Implementation for User Story 1

- [X] T010 [US1] Implement `GET /health` route returning the `HealthStatus` shape from `contracts/health-api.yaml`, no authentication required (FR-001, FR-002) in `backend/src/api/health.py` — makes T007 pass
- [X] T011 [US1] Mount the health router into the FastAPI app in `backend/src/main.py` (depends on T004, T010)
- [X] T012 [P] [US1] Implement `HealthService` calling `GET /health` in `frontend/src/app/health/health.service.ts` (depends on T005) — makes T008 pass
- [X] T013 [US1] Implement `HealthStatusComponent` consuming `HealthService` and rendering healthy/unreachable/checking states (FR-004) in `frontend/src/app/health/health-status.component.ts` (depends on T006, T012) — makes T009 pass
- [X] T014 [US1] Integrate `HealthStatusComponent` into the app shell in `frontend/src/app/app.component.ts` (depends on T013)
- [X] T015 [US1] Manually validate Acceptance Scenarios 1–3 by following quickstart.md steps 1–4 (depends on T011, T014) — validated at the HTTP/CORS level via curl (no browser extension available this session); frontend rendering behavior for each state is covered by T009's component tests

**Checkpoint**: At this point, User Story 1 is fully functional and independently testable — this is the entire MVP for this feature.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation for the skeleton

- [X] T016 [P] Document local run instructions (backend + frontend) in `README.md`, referencing `specs/001-skeleton-health-check/quickstart.md`
- [X] T017 Run full quickstart.md validation (backend `pytest`, frontend `ng test`, and all manual scenarios) and confirm SC-001–SC-004 are met (depends on T015, T016)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS User Story 1
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **Polish (Phase 4)**: Depends on User Story 1 completion

### Within User Story 1

- Tests (T007–T009) MUST be written and FAIL before their corresponding implementation tasks (Constitution Principle I)
- Backend route (T010) before mounting it (T011)
- Frontend service (T012) before the component that consumes it (T013)
- Component (T013) before integrating it into the app shell (T014)
- Implementation complete (T011, T014) before manual scenario validation (T015)

### Parallel Opportunities

- T003 (frontend scaffold) can run in parallel with T001–T002 (backend setup) — different projects
- T005 and T006 (Foundational) can run in parallel — different frontend files
- T007, T008, T009 (all US1 tests) can run in parallel — three different files, no shared dependencies
- T012 (frontend service implementation) can run in parallel with T010–T011 (backend implementation) — independent stacks
- T016 (documentation) can run in parallel with T017's prerequisites being finished, though T017 itself is the final gate

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Write failing backend tests for GET /health in backend/tests/unit/test_health.py"
Task: "Write failing tests for HealthService in frontend/src/app/health/health.service.spec.ts"
Task: "Write failing tests for HealthStatusComponent in frontend/src/app/health/health-status.component.spec.ts"

# Once tests exist, backend and frontend implementation can proceed in parallel:
Task: "Implement GET /health route in backend/src/api/health.py"
Task: "Implement HealthService in frontend/src/app/health/health.service.ts"
```

---

## Implementation Strategy

### MVP First (and Only) Scope

This feature has exactly one user story, which is itself the MVP:

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks the user story)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run quickstart.md end-to-end (T015, T017)
5. Complete Phase 4: Polish

There is no incremental multi-story delivery here — the "walking skeleton" is complete when Phase 3 passes its independent test.

---

## Notes

- [P] tasks = different files, no dependencies
- [US1] label maps every user-facing task to the feature's single user story for traceability
- Verify tests fail before implementing (Constitution Principle I is NON-NEGOTIABLE for this project)
- Commit after each task or logical group
- No dependency checks, persistence, or authentication are in scope for this feature (see spec.md Assumptions) — do not add them here
