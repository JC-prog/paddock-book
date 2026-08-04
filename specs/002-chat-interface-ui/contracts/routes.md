# UI Contract: Client-Side Routes

This feature introduces no network/API contract (spec Assumptions — no backend
integration). The contract that matters here is the **routing contract**
resolved during `/speckit-clarify`: which address shows which page.

| Path | Component (lazy-loaded) | Purpose | Source |
|---|---|---|---|
| `/` | `ChatPageComponent` (`features/chat/`) | Navbar + chatbox + textbox — the chat interface (User Story 1, 2) | FR-001–FR-009 |
| `/health` | `HealthStatusComponent` (`features/health/`, unchanged from feature 001) | Backend health indicator, relocated off the root page (User Story 3) | FR-010 |

**Contract guarantees**:
- Navigating to `/` MUST NOT render the health-status indicator (spec User Story
  3, Acceptance Scenario 2).
- Navigating to `/health` MUST render the existing healthy/unreachable/checking
  indicator behavior from feature 001, unchanged (spec User Story 3, Acceptance
  Scenario 1).
- Both routes render inside the same app shell (navbar always visible — see
  research.md).

Any future addition of a new top-level page MUST add a row to this table and a
corresponding route in `app.routes.ts`, per Constitution Principle V (every
domain gets its own `features/<name>/` folder, lazy-loaded via the router).
