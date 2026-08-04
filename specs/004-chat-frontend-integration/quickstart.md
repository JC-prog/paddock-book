# Quickstart: Chat Frontend-Backend Integration

Validates the integration end-to-end per the user story in
[spec.md](./spec.md). Contracts: the unchanged
[003 chat-api.md](../003-chat-api-sse/contracts/chat-api.md) and the updated
[cors-policy.md](./contracts/cors-policy.md). Data shape:
[data-model.md](./data-model.md).

## Prerequisites

- Backend and frontend both set up per the root `README.md`

## 1. Run both sides

```bash
# Terminal 1
cd backend && source .venv/bin/activate && uvicorn src.main:app --reload --port 8000

# Terminal 2
cd frontend && npx ng serve --port 4200
```

## 2. Send a message and watch the reply stream in (Acceptance Scenarios 1–3)

Open `http://localhost:4200`, type a message, and send it.

**Expected**: your message appears as a bubble (as before, feature 002).
Shortly after, a second, visually distinct bubble appears and its text
grows incrementally — "Hello," then "Hello, this" then "Hello, this is" and
so on — until it reads "Hello, this is a test response." and stops
changing.

## 3. Verify sending is blocked while a reply is in flight (FR-007)

While the reply from step 2 is still streaming (or immediately after
sending a new message), try to send another message.

**Expected**: the send action (button and Enter key) is disabled/ineffective
until the current reply finishes.

## 4. Verify the failure path (Acceptance Scenario 4, FR-005)

Stop the backend process, then send a message.

**Expected**: within 10 seconds, the conversation shows a clear failure
indication for that message — your own message bubble remains visible; no
message is left silently waiting forever. Restart the backend and confirm
sending works again afterward.

## 5. Run the automated tests

```bash
# Backend
cd backend && source .venv/bin/activate && pytest tests/unit

# Frontend
cd frontend && npx vitest run
```

**Expected**: all tests pass, including `ChatApiService` (mocked
fetch/stream: multi-word emission, clean completion, timeout, dropped
connection), `ChatService` (message list orchestration, `isSending`),
`ChatInputComponent` (disabled while sending), and `MessageBubbleComponent`
(styling by sender/status).
