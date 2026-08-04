---

description: "Task list for Chat Interface UI"
---

# Tasks: Chat Interface UI

**Input**: Design documents from `/specs/002-chat-interface-ui/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/routes.md, quickstart.md

**Tests**: Included and required for behavioral/logic code — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates a failing test before implementation for every requirement. Pure Tailwind styling tasks (User Story 2) are validated manually per quickstart.md instead, since visual/responsive layout isn't meaningfully asserted by Jasmine unit tests — this matches how spec.md phrases SC-002/SC-003 ("verified through manual testing").

**Organization**: Tasks are grouped by user story from spec.md (US1 = P1, US2 = P2, US3 = P3), matching the amended Constitution Principle V folder conventions (`shared/navbar/`, `features/chat/`, `features/health/`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths below are all under `frontend/src/app/` unless noted otherwise

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add Tailwind CSS to the frontend build

- [X] T001 Add `tailwindcss`, `postcss`, and `autoprefixer` as devDependencies in `frontend/package.json`
- [X] T002 [P] Create `frontend/tailwind.config.js` with `content: ["src/**/*.{html,ts}"]`
- [X] T003 [P] Create `frontend/postcss.config.js` with the `tailwindcss` and `autoprefixer` plugins
- [X] T004 Add `@tailwind base; @tailwind components; @tailwind utilities;` to `frontend/src/styles.css`

**Checkpoint**: `ng serve` picks up Tailwind utility classes with no additional build config.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: App shell (navbar + router outlet) and routing infrastructure that every story's route depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 [P] Write failing test for `NavbarComponent` rendering the application's branding in `frontend/src/app/shared/navbar/navbar.component.spec.ts`
- [X] T006 [P] Implement `NavbarComponent` (static branding only, per spec Assumptions) in `frontend/src/app/shared/navbar/navbar.component.ts` — makes T005 pass
- [X] T007 [P] Create `frontend/src/app/app.routes.ts` with an empty `Routes` array (routing infrastructure ready; routes are added per-story below)
- [X] T008 [P] Register `provideRouter(routes)` in `frontend/src/app/app.config.ts` (depends on T007)
- [X] T009 Update `frontend/src/app/app.component.html`/`.ts` to render `<app-navbar />` + `<router-outlet />`, removing the hardcoded `<app-health-status>` embed and its import from feature 001 (depends on T006, T008)

**Checkpoint**: App shell renders the navbar and an empty router outlet; no route resolves to anything yet.

---

## Phase 3: User Story 1 - Compose and view messages as chat bubbles (Priority: P1) 🎯 MVP

**Goal**: A visitor can type a message on the root page and see it appear as a bubble in the chatbox, with no backend involved (spec User Story 1).

**Independent Test**: Load the root page, type a message, submit it (Enter or send button), and confirm it appears as a new bubble — fully verifiable with no network connection.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (Constitution Principle I)**

- [X] T010 [P] [US1] Write failing tests for `ChatService` — rejects empty/whitespace-only text (FR-006), appends valid messages preserving order (FR-002) — in `frontend/src/app/features/chat/chat.service.spec.ts`
- [X] T011 [P] [US1] Write failing tests for `ChatInputComponent` — Enter submits, Shift+Enter inserts a newline instead of submitting (FR-004), send button submits, textbox clears after submit (FR-007), empty/whitespace submit is a no-op (FR-006) — in `frontend/src/app/features/chat/chat-input.component.spec.ts`
- [X] T012 [P] [US1] Write failing tests for `MessageBubbleComponent` — renders given message text, preserves embedded line breaks (FR-005, multi-line edge case) — in `frontend/src/app/features/chat/message-bubble.component.spec.ts`
- [X] T013 [P] [US1] Write failing tests for `ChatBoxComponent` — renders bubbles in the order messages were added (FR-002), scrolls to keep the newest message visible when the list grows (FR-008) — in `frontend/src/app/features/chat/chat-box.component.spec.ts`

### Implementation for User Story 1

- [X] T014 [US1] Implement `ChatService` with a `signal<ChatMessage[]>` and a `sendMessage(text)` method that trims and rejects empty input before appending (data-model.md) in `frontend/src/app/features/chat/chat.service.ts` — makes T010 pass
- [X] T015 [P] [US1] Implement `MessageBubbleComponent` in `frontend/src/app/features/chat/message-bubble.component.ts` — makes T012 pass
- [X] T016 [US1] Implement `ChatBoxComponent` — renders a `MessageBubbleComponent` per message, auto-scrolls via a `ViewChild` + `effect()` on the message signal (research.md) — in `frontend/src/app/features/chat/chat-box.component.ts` (depends on T014, T015) — makes T013 pass
- [X] T017 [US1] Implement `ChatInputComponent` — multi-line textarea wired to `ChatService.sendMessage()` via Enter/Shift+Enter/send button (research.md, FR-004) — in `frontend/src/app/features/chat/chat-input.component.ts` (depends on T014) — makes T011 pass
- [X] T018 [US1] Implement `ChatPageComponent` composing `ChatBoxComponent` + `ChatInputComponent` in `frontend/src/app/features/chat/chat-page.component.ts` (depends on T016, T017)
- [X] T019 [US1] Add the root route (`''` → `ChatPageComponent`, lazy via `loadComponent`) to `frontend/src/app/app.routes.ts` per `contracts/routes.md` (depends on T007, T018)
- [X] T020 [US1] Manually validate Acceptance Scenarios 1–5 via quickstart.md step 2 (depends on T019) — verified via dev server (lazy `chat-page-component` chunk confirmed loading, Tailwind base layer compiling into bundle); no browser extension available this session for a visual walkthrough, so Scenarios 1–5 rest on the component test suite (T010–T013), which exercises each one directly

**Checkpoint**: At this point, User Story 1 is fully functional and independently testable — this is the MVP.

---

## Phase 4: User Story 2 - Use the interface comfortably on any device (Priority: P2)

**Goal**: The navbar, chatbox, and textbox lay out correctly at mobile, tablet, and desktop widths (spec User Story 2).

**Independent Test**: Load the root page and resize the viewport across mobile/tablet/desktop widths, confirming all three elements remain visible and usable with no horizontal scrolling.

- [X] T021 [P] [US2] Apply responsive Tailwind utility classes to `NavbarComponent`'s template in `frontend/src/app/shared/navbar/navbar.component.ts`
- [X] T022 [P] [US2] Apply responsive Tailwind utility classes to `ChatBoxComponent`'s template (scrollable, flexible-height container) in `frontend/src/app/features/chat/chat-box.component.ts` — also added the actual bubble visual (rounded, colored, right-aligned) to `message-bubble.component.ts`, since FR-005's "distinct visual bubble" needed styling that Jasmine tests can't meaningfully assert, matching this phase's manual-validation approach
- [X] T023 [P] [US2] Apply responsive Tailwind utility classes to `ChatInputComponent`'s template (full-width on mobile, constrained on desktop) in `frontend/src/app/features/chat/chat-input.component.ts`
- [X] T024 [US2] Apply responsive Tailwind layout (flex/grid sizing navbar + chatbox + input together) to `ChatPageComponent`'s template in `frontend/src/app/features/chat/chat-page.component.ts` (depends on T021, T022, T023) — used Angular `host` bindings on `ChatPageComponent`/`ChatBoxComponent` for flex sizing, and updated `app.component.html`'s shell wrapper (`flex h-screen flex-col`) to `app.component.html` since the routed page needs a sized flex-column ancestor to fill
- [X] T025 [US2] Manually validate Acceptance Scenarios 1–3 at 375px / 768px / 1280px+ via quickstart.md step 3 (depends on T024) — verified the `sm:` breakpoint media queries and utility classes actually compiled into the served bundle; no browser extension available this session for a visual walkthrough at each width

**Checkpoint**: User Stories 1 and 2 both work — the chat interface is functional and responsive.

---

## Phase 5: User Story 3 - Check backend health status at its own address (Priority: P3)

**Goal**: The existing health-status indicator (feature 001) is reachable at `/health` and no longer shown on the root page (spec User Story 3, FR-010).

**Independent Test**: Navigate directly to `/health` and confirm the existing healthy/unreachable/checking indicator still renders — independent of anything on the chat page.

- [X] T026 [P] [US3] Write failing test confirming the `'health'` route resolves to `HealthStatusComponent` in `frontend/src/app/app.routes.spec.ts`
- [X] T027 [US3] Add the `'health'` route (→ `HealthStatusComponent` from `features/health/`, lazy via `loadComponent`) to `frontend/src/app/app.routes.ts` per `contracts/routes.md` (depends on T007) — makes T026 pass
- [X] T028 [US3] Manually validate Acceptance Scenarios 1–2 via quickstart.md step 4 (depends on T019, T027) — confirmed `/health` returns 200 from the dev server and resolves to `HealthStatusComponent` (T026's test), and confirmed via search that no chat file or `app.component.*` references `HealthStatusComponent`/`app-health-status`; no browser extension available this session for a visual walkthrough

**Checkpoint**: All three user stories are independently functional — chat at `/`, health check at `/health`.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all three stories

- [X] T029 Run full quickstart.md validation (`ng test`, plus all manual scenarios from steps 2–4) and confirm SC-001–SC-004 are met (depends on T020, T025, T028) — final `ng test` run: 24/24 passing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on User Story 1 (styles components that US1 creates) — not independent of US1's files, though it is a distinct, independently-verifiable increment
- **User Story 3 (Phase 5)**: Depends on Foundational phase completion; independent of US1/US2 except for T028's manual check of scenario 2, which needs the root page (US1) to exist to confirm it does *not* show the health indicator
- **Polish (Phase 6)**: Depends on all three stories being complete

### Within Each User Story

- Tests MUST be written and FAIL before their corresponding implementation tasks (Constitution Principle I)
- `ChatService` (T014) before the components that consume it (T016, T017)
- `MessageBubbleComponent` (T015) before `ChatBoxComponent` (T016), which renders it
- `ChatBoxComponent` + `ChatInputComponent` (T016, T017) before `ChatPageComponent` (T018), which composes them
- `ChatPageComponent` (T018) before the route that points to it (T019)

### Parallel Opportunities

- T002, T003 (Setup) can run in parallel — different config files
- T005 and T007 (Foundational) can run in parallel — unrelated files (navbar test vs. empty routes scaffold)
- T006 and T008 (Foundational) can run in parallel with each other once their respective predecessors (T005, T007) are done
- T010, T011, T012, T013 (all US1 tests) can run in parallel — four different files
- T015 (`MessageBubbleComponent`) can run in parallel with T014 (`ChatService`) — no dependency between them
- T021, T022, T023 (US2 styling) can run in parallel — three different component files
- T026 (US3 test) can run in parallel with any US1/US2 task — unrelated file

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Write failing tests for ChatService in frontend/src/app/features/chat/chat.service.spec.ts"
Task: "Write failing tests for ChatInputComponent in frontend/src/app/features/chat/chat-input.component.spec.ts"
Task: "Write failing tests for MessageBubbleComponent in frontend/src/app/features/chat/message-bubble.component.spec.ts"
Task: "Write failing tests for ChatBoxComponent in frontend/src/app/features/chat/chat-box.component.spec.ts"

# ChatService and MessageBubbleComponent implementations are independent:
Task: "Implement ChatService in frontend/src/app/features/chat/chat.service.ts"
Task: "Implement MessageBubbleComponent in frontend/src/app/features/chat/message-bubble.component.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run quickstart.md step 2 (T020)
5. Deploy/demo if ready — the chat interface works, even without polished responsiveness or the relocated health check

### Incremental Delivery

1. Complete Setup + Foundational → shell and routing infrastructure ready
2. Add User Story 1 → chat works on the root page → validate (MVP!)
3. Add User Story 2 → chat is responsive across devices → validate
4. Add User Story 3 → health check moves to `/health` → validate
5. Complete Polish → full quickstart.md validation

---

## Notes

- [P] tasks = different files, no dependencies
- [US1]/[US2]/[US3] labels map every user-facing task to its spec.md story for traceability
- Verify tests fail before implementing (Constitution Principle I is NON-NEGOTIABLE for this project)
- Commit after each task or logical group
- No backend/API calls, no message persistence, and no simulated replies are in scope for this feature (see spec.md Assumptions) — do not add them here
