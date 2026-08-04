# Feature Specification: Chat Frontend-Backend Integration

**Feature Branch**: `004-chat-frontend-integration`

**Created**: 2026-08-05

**Status**: Draft

**Input**: User description: "Integrate chat frontend ui to the backend chat api. Uses should be able to send messages and receive messages from the backend. The structure of the code must have separation of concerns."

## Clarifications

### Session 2026-08-05

- Q: Can the user send another message while a previous reply is still streaming in? → A: No — block sending until the current reply completes, for a simpler one-turn-at-a-time mental model.
- Q: Is there a maximum time the interface waits before treating an unresponsive backend as failed? → A: 10 seconds.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the backend's reply appear in the conversation (Priority: P1)

As a user of the chat interface, when I send a message, I want the backend's
reply to appear in the conversation as its own bubble, so that the chat
interface is actually backed by a real request instead of only showing my
own message back to me.

**Why this priority**: This is the entire point of the integration — without
it, sending a message still does nothing beyond what the chat interface
already did on its own (feature 002), and the chat address built in feature
003 is never actually used.

**Independent Test**: Send a message with the backend running and confirm
that, after the user's own message bubble appears, a reply bubble from the
backend also appears and eventually stops changing (the reply is complete).

**Acceptance Scenarios**:

1. **Given** the chat interface is loaded and the backend is reachable,
   **When** the user sends a message, **Then** their own message appears as
   a bubble (as before) and the backend's reply subsequently appears as a
   separate bubble, visually distinguishable from the user's own messages.
2. **Given** the backend's reply is arriving, **When** more of it arrives,
   **Then** the reply bubble updates to show the growing text incrementally,
   rather than appearing all at once only after the full reply is ready.
3. **Given** the backend's reply has finished arriving, **When** no more of
   it follows, **Then** the reply bubble stops updating and is treated as
   complete.
4. **Given** the backend is unreachable or returns an error, **When** the
   user sends a message, **Then** the conversation clearly shows that this
   specific message did not get a reply, rather than leaving the user
   waiting indefinitely or failing silently.
5. **Given** a reply is still arriving for a previously sent message,
   **When** the user tries to send another message, **Then** the interface
   prevents it — sending stays disabled until the current reply completes
   (or fails).

---

### Edge Cases

- What happens when the backend takes a long time to start replying? The
  user should be able to tell a reply is expected/in progress rather than
  assuming nothing is happening (ties to Acceptance Scenario 4's error
  handling, and to the specific behavior chosen for Acceptance Scenario 4's
  error case).
- What happens when the backend connection drops partway through a reply?
  The partial reply that already arrived should remain visible, and the
  conversation should indicate that it didn't finish normally, using the
  same failure indication chosen for Acceptance Scenario 4.
- What happens when the user sends a message with the backend unreachable
  from the very start (e.g. not running)? Same failure indication as
  Acceptance Scenario 4, triggered after waiting up to 10 seconds for the
  reply to begin (see SC-003), rather than waiting indefinitely.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When the user sends a message, the system MUST send it to the
  backend's chat capability (built in feature 003) in addition to showing it
  as a bubble locally (existing behavior from feature 002).
- **FR-002**: The system MUST render the backend's reply as its own bubble,
  visually distinguishable from the user's own message bubbles.
- **FR-003**: The system MUST update the reply bubble incrementally as more
  of the reply arrives, rather than waiting for the entire reply before
  showing anything.
- **FR-004**: The system MUST treat the reply as complete once no further
  content arrives for it, and MUST NOT continue to indicate it is still in
  progress after that point.
- **FR-005**: The system MUST clearly indicate, within the conversation, when
  a specific message's reply failed or the backend was unreachable, rather
  than leaving that message's reply visibly stuck or silently absent. If no
  part of a reply has arrived within 10 seconds of sending, the system MUST
  treat that message as failed.
- **FR-006**: The system MUST NOT lose or hide the user's own message when
  its reply fails — the user's message bubble remains in the conversation
  regardless of what happens with the reply.
- **FR-007**: The system MUST prevent the user from sending a new message
  while a previously sent message's reply is still arriving; sending
  becomes available again once that reply completes or fails.

### Key Entities

- **Chat Message**: Extends the Chat Message from feature 002. In addition
  to its text content and order, each message now has a sender (the user or
  the backend) and a status reflecting whether it is still arriving,
  complete, or failed — needed to render bubbles differently by sender and
  to support Acceptance Scenarios 2–4.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After sending a message with the backend reachable, a user
  sees the backend's reply begin appearing within 2 seconds.
- **SC-002**: 100% of replies in testing are shown building up incrementally
  (more than one visible update) rather than appearing as a single block,
  matching the backend's incremental delivery (feature 003).
- **SC-003**: 100% of messages sent while the backend is unreachable result
  in a visible failure indication for that message within 10 seconds,
  verified through testing, with no message left in an ambiguous
  "waiting forever" state.
- **SC-004**: A user can always tell, for any message they've sent, whether
  its reply is still arriving, complete, or failed, just by looking at the
  conversation.

## Assumptions

- This feature is full-stack: it includes both the frontend calling logic
  and any minimal backend configuration needed for the frontend's requests
  to actually reach the chat address (e.g. the backend currently only
  allows cross-origin requests for the health-check address, not the chat
  address — this policy will need extending as part of this feature).
- The reply's content is still the fixed placeholder text from feature 003
  ("Hello, this is a test response.") — this feature wires up real request/
  response plumbing, but does not change what the backend replies with.
- No conversation history is persisted or sent to the backend as context;
  each message is still an independent, stateless request, consistent with
  feature 003's design. Multi-turn context is out of scope.
- Rendering the reply incrementally as it arrives (rather than buffering the
  full reply before showing anything) is assumed to be the point of having
  built an incrementally-streaming backend in feature 003, so no
  clarification was needed for this specific point.
- No new authentication is introduced; the chat address remains
  unauthenticated as established in feature 003.
