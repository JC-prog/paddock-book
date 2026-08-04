# Implementation Plan: Chat Interface UI

**Branch**: `002-chat-interface-ui` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-chat-interface-ui/spec.md`

## Summary

Build a static (no backend) chat interface as the frontend's root page: a shared
navbar, a chatbox that lists messages as bubbles, and a textbox that lets the user
compose and submit a message (Enter key or send button), appended locally with no
network call. Add Angular routing so the existing health-status indicator (feature
001) moves from the root page to its own `/health` address (FR-010), and adopt
Tailwind CSS for responsive styling (FR-009, SC-002), per spec.md.

## Technical Context

**Language/Version**: TypeScript 5.x (Angular 18) — frontend only; no backend
changes in this feature (explicitly no API, per spec Assumptions)

**Primary Dependencies**: `@angular/router` (already installed, not yet wired up);
Tailwind CSS v3 + PostCSS + Autoprefixer (new devDependencies, for FR-009)

**Storage**: N/A — chat messages live only in in-memory component/service state for
the current page session (spec Key Entities)

**Testing**: Jasmine/Karma (Angular CLI defaults), consistent with feature 001

**Target Platform**: Browser SPA, served by the Angular dev server (unchanged from
feature 001)

**Project Type**: Web application, frontend-only change (Option 2 structure,
`frontend/` side only)

**Performance Goals**: Submitted message renders as a bubble within 2 seconds
(SC-001) — trivially met since no network call is involved

**Constraints**: No backend/API calls in this feature (spec Assumptions); layout
MUST remain usable with no horizontal scrolling at mobile (375px), tablet (768px),
and desktop (1280px+) widths (SC-002)

**Scale/Scope**: Single-user browser session; no persistence, no concurrency
concerns

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature | Status |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Yes — `ChatService`, `ChatInputComponent`, `ChatBoxComponent`/`MessageBubbleComponent`, `NavbarComponent`, and the route config each need a failing test before implementation | PASS (enforced at task-generation/implementation time) |
| II. Comprehensive Unit Testing | Yes — empty/whitespace rejection, message ordering, Enter-key and button submit paths, and route-to-component mapping are all testable with no live dependency (there is none here) | PASS |
| III. API Contract Consistency | Not applicable — this feature touches no backend and makes no API calls; `contracts/health-api.yaml` from feature 001 is unaffected | PASS (N/A) |
| IV. Clean Code & Readability | Yes — chat UI is split into single-responsibility components (input, bubble, box, navbar) rather than one large component | PASS |
| V. Separation of Concerns | Yes — chat feature lives under `features/chat/`, the navbar under `shared/` (per the amended folder conventions), and `features/health/` is now reached via a lazy-loaded route instead of being hardcoded into the app shell | PASS |

No violations. Complexity Tracking is not needed.

**Post-Phase 1 re-check**: `data-model.md` (one transient, unpersisted entity),
`contracts/routes.md` (two lazy-loaded routes), and `quickstart.md` introduce
nothing beyond what Phase 0 research already accounted for. All five principles
still PASS; no new complexity, dependency, or scope was added during design.

## Project Structure

### Documentation (this feature)

```text
specs/002-chat-interface-ui/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
frontend/
├── tailwind.config.js       # new — content globs over src/**/*.{html,ts}
├── postcss.config.js        # new — tailwindcss + autoprefixer
├── src/
│   ├── styles.css            # modified — add @tailwind base/components/utilities
│   └── app/
│       ├── app.component.ts      # modified — shell: <app-navbar> + <router-outlet>
│       ├── app.component.html
│       ├── app.config.ts         # modified — add provideRouter(routes)
│       ├── app.routes.ts         # new — '' → chat (lazy), 'health' → health (lazy)
│       ├── shared/
│       │   └── navbar/
│       │       ├── navbar.component.ts
│       │       └── navbar.component.spec.ts
│       └── features/
│           ├── health/                      # existing (feature 001), unchanged internals
│           │   ├── health.service.ts
│           │   ├── health.service.spec.ts
│           │   ├── health-status.component.ts
│           │   └── health-status.component.spec.ts
│           └── chat/                        # new
│               ├── chat.service.ts
│               ├── chat.service.spec.ts
│               ├── chat-page.component.ts        # composes chat-box + chat-input
│               ├── chat-page.component.spec.ts
│               ├── chat-box.component.ts
│               ├── chat-box.component.spec.ts
│               ├── message-bubble.component.ts
│               ├── message-bubble.component.spec.ts
│               ├── chat-input.component.ts
│               └── chat-input.component.spec.ts

backend/                      # untouched by this feature
```

**Structure Decision**: Option 2 (web application), frontend-only. Follows the
Constitution's amended Principle V conventions: `shared/navbar/` for the
reusable, business-logic-free navbar; `features/chat/` for the new domain,
`features/health/` for the existing one — both now reached through
`app.routes.ts` using `loadComponent` (lazy-loaded), as the amended principle
requires for everything under `features/`. No `core/` folder is added yet since
this feature introduces no cross-cutting singleton service, interceptor, or
guard — it will appear when one is actually needed rather than as an empty
placeholder.

## Complexity Tracking

*Not applicable — the Constitution Check above has no violations to justify.*
