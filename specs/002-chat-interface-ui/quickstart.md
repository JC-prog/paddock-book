# Quickstart: Chat Interface UI

Validates the chat interface end-to-end per the user stories in
[spec.md](./spec.md). Routing contract: [contracts/routes.md](./contracts/routes.md).
Data shape: [data-model.md](./data-model.md). No backend is required for this
feature — everything here runs against the frontend alone.

## Prerequisites

- Node.js (LTS) and npm (already set up from feature 001)
- `frontend/node_modules` installed (`npm install`, if not already done)

## 1. Run the frontend

```bash
cd frontend
npx ng serve --port 4200
```

**Expected**: dev server starts on `http://localhost:4200`.

## 2. Verify the chat interface (User Story 1)

Open `http://localhost:4200`.

**Expected**: a navbar at the top, an empty chatbox, and a textbox below it.

- Type a message and press **Enter**. **Expected**: the message appears as a
  bubble in the chatbox; the textbox clears (FR-004, FR-005, FR-007).
- Type a message and click the **send** control instead of pressing Enter.
  **Expected**: same result (FR-004).
- Send several messages in a row. **Expected**: each appears in order, and the
  chatbox auto-scrolls to keep the latest one visible (FR-008, SC-001).
- Try submitting with an empty or whitespace-only textbox. **Expected**: no
  bubble is added (FR-006, SC-003).

## 3. Verify responsiveness (User Story 2)

With the browser's device toolbar (or by resizing the window), check the
interface at roughly:

- **375px** (mobile), **768px** (tablet), **1280px+** (desktop)

**Expected** at every width: navbar, chatbox, and textbox are all visible with
no horizontal scrollbar and no overlapping elements (FR-009, SC-002). Resize
while messages are present — **expected**: no message content is lost.

## 4. Verify the health check moved to `/health` (User Story 3)

Navigate to `http://localhost:4200/health`.

**Expected**: the existing healthy/unreachable/checking indicator from feature
001 renders here (FR-010).

Navigate back to `http://localhost:4200/`.

**Expected**: no health-status indicator appears on the chat page.

## 5. Run the automated tests

```bash
cd frontend
npx ng test --watch=false
```

**Expected**: all tests pass, including `ChatService` (empty-message
rejection, ordering), `ChatInputComponent` (Enter key + button submit),
`ChatBoxComponent`/`MessageBubbleComponent` (bubble rendering), `NavbarComponent`,
and the route configuration.
