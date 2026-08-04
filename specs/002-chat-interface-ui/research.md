# Phase 0 Research: Chat Interface UI

No `NEEDS CLARIFICATION` markers remain in the Technical Context — the one open
question from spec.md (what happens to the health-status indicator) was resolved
during `/speckit-clarify`. This document records the supporting technical
decisions needed to execute the plan.

## Decision: Tailwind CSS v3 via Angular CLI's built-in PostCSS support

- **Rationale**: Angular CLI ≥17 (including our Angular 18 project) applies any
  `postcss.config.js` found at the project root automatically — no custom webpack
  config or `ng add` schematic is required. Installing `tailwindcss`, `postcss`,
  and `autoprefixer` as devDependencies, adding a `tailwind.config.js` with
  `content: ["src/**/*.{html,ts}"]`, and adding the three `@tailwind` directives
  to `src/styles.css` is sufficient to satisfy FR-009/SC-002 (responsive layout).
- **Alternatives considered**: Tailwind v4 (new CSS-first config, Vite-oriented
  tooling) — riskier pairing with Angular 18's current (non-Vite) builder at this
  point; v3 is the well-documented, stable path. Hand-written responsive CSS
  (flexbox/grid + media queries) — would work but the user explicitly asked for
  Tailwind CSS.

## Decision: Angular Router with lazy-loaded standalone components

- **Rationale**: The amended Constitution Principle V requires everything under
  `features/<name>/` to be lazy-loaded via the router. `@angular/router` is
  already an installed dependency (Angular CLI 18 includes it even when
  `--routing=false` is passed at `ng new` time), so no new package is needed —
  only `provideRouter(routes)` in `app.config.ts` and an `app.routes.ts` using
  `loadComponent: () => import(...).then(m => m.XComponent)` for both the chat
  page (`''`) and the health page (`'health'`).
- **Alternatives considered**: Eagerly-imported `component:` routes — simpler,
  but directly violates the amended Principle V's explicit "lazy-loaded via the
  router" requirement for `features/`.

## Decision: Navbar renders on every route, inside the app shell

- **Rationale**: `AppComponent`'s template becomes `<app-navbar />` +
  `<router-outlet />`, so the navbar is unaffected by which route is active. This
  wasn't asked about directly in spec.md, but it's the natural reading of FR-001
  ("the root page MUST display a navbar") combined with User Story 3's
  acceptance scenario 2 ("no health-status indicator is shown on the root page")
  — nothing in the spec says the navbar should disappear on `/health`, and a
  shell-level navbar is standard SPA structure.
- **Alternatives considered**: Per-route navbar (duplicated inside both the chat
  and health page components) — rejected as needless duplication for a
  business-logic-free, purely presentational element (Constitution Principle IV).

## Decision: Chat message state via a signal-based `ChatService`

- **Rationale**: Angular 17+/18's `signal()` is the idiomatic, minimal-boilerplate
  way to hold and react to local UI state like an in-memory message list — no
  RxJS subscription management needed for a value that's never asynchronous.
  `ChatService.sendMessage(text)` trims the input, rejects empty/whitespace-only
  text (FR-006), and appends a new `ChatMessage` to the signal; components read
  the signal directly in their templates.
- **Alternatives considered**: `BehaviorSubject` — more ceremony (subscribe/
  unsubscribe or `async` pipe) for a synchronous, purely local value. Storing the
  message array directly in `ChatPageComponent` with no service — would work for
  a single component, but a service keeps the list independently unit-testable
  (Constitution Principle II) without mounting the whole component tree.

## Decision: Auto-scroll via a template reference + effect

- **Rationale**: `ChatBoxComponent` holds a `ViewChild` reference to its
  scrollable container and uses Angular's `effect()` to call
  `scrollTop = scrollHeight` whenever the message signal changes, satisfying
  FR-008. This runs after Angular's change detection updates the DOM, so the
  newly-rendered bubble's height is already accounted for.
- **Alternatives considered**: `ngAfterViewChecked` with a manual dirty flag —
  works but is more error-prone (easy to over- or under-fire); `effect()` is the
  modern, more precise mechanism.

## Decision: All bubbles share one visual style (no per-sender variants)

- **Rationale**: Per spec Assumptions, only the user's own messages appear
  (no simulated reply), so there's no "other party" to visually distinguish —
  `MessageBubbleComponent` needs exactly one bubble style, right-aligned per
  common chat-UI convention for the sender's own messages.
- **Alternatives considered**: Building a `sender` field / left-right variants
  into `MessageBubbleComponent` now — rejected as speculative (Constitution
  Principle IV); add it when a real second sender (e.g. an assistant reply)
  exists.
