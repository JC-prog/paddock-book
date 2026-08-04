# Feature Specification: Chat API with Streamed Responses

**Feature Branch**: `003-chat-api-sse`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "Chat feature for the app, endpoint is /v1/chat, this acts as the primary way of chatting wit h the backend. User would be able to send a message to the backend and returned a placeholder response. The message would be received in a router and return a \"Hello\" back. I want to use Server Sent events."

## Clarifications

### Session 2026-08-05

- Q: Should the placeholder reply stream as a single event or multiple incremental events? → A: Multiple incremental events, using a longer placeholder ("Hello, this is a test response.") split word-by-word, since a single-word reply can't meaningfully demonstrate incremental streaming.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Send a message and receive a streamed reply (Priority: P1)

As a client application talking to PaddockBook's backend, I want to send a
chat message to the backend's primary chat address and receive a reply
delivered as a stream, so that the wiring for real-time conversational
responses is proven out before any real response-generation logic exists.

**Why this priority**: This is the entire feature — a chat address that
accepts a message and streams a reply back. Without it, there is no chat
capability at all, placeholder or otherwise.

**Independent Test**: Send a message to the chat address and confirm a
streamed response is received and completes — fully verifiable without any
real response-generation logic behind it.

**Acceptance Scenarios**:

1. **Given** the backend is running, **When** a client sends a message to the
   chat address, **Then** the client receives a streamed reply containing the
   placeholder text.
2. **Given** a client is receiving the streamed reply, **When** the reply
   arrives, **Then** it arrives as multiple discrete events (word-by-word)
   rather than as a single event, so the client can observe it building up
   incrementally.
3. **Given** a client has received the full streamed reply, **When** no more
   data follows, **Then** the client can detect that the stream has ended.
4. **Given** a client sends a request with no message content, **When** the
   backend receives it, **Then** the backend rejects the request rather than
   returning a placeholder reply.
5. **Given** a client disconnects while a reply is streaming, **When** the
   backend detects the disconnect, **Then** it stops sending further data for
   that request without error.

---

### Edge Cases

- What happens when the client sends an empty or whitespace-only message?
  The backend must reject the request rather than silently returning a
  placeholder reply (Acceptance Scenario 4).
- What happens when the client disconnects mid-stream? The backend must stop
  processing/sending for that request without raising an unhandled error
  (Acceptance Scenario 5).
- What happens when multiple clients send messages at the same time? Each
  request must be handled independently, with no shared state between them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend MUST expose a chat capability at `/v1/chat` that
  accepts a message from a client.
- **FR-002**: The backend MUST reject requests where the message is missing,
  empty, or whitespace-only, rather than returning a reply for them.
- **FR-003**: Upon receiving a valid message, the backend MUST respond using
  a streamed connection (Server-Sent Events) rather than a single blocking
  reply.
- **FR-004**: The streamed reply MUST deliver the placeholder text "Hello,
  this is a test response." as multiple incremental events, one word at a
  time, rather than as a single event.
- **FR-005**: The backend MUST signal to the client when the streamed reply
  is complete (the connection closes once the full placeholder reply has
  been sent).
- **FR-006**: The backend MUST NOT require authentication on this address, to
  keep it consistent with the rest of the application skeleton.
- **FR-007**: The backend MUST handle each chat request independently, with
  no shared or blocking state across concurrent requests.

### Key Entities

- **Chat Request**: A single message sent by a client to the chat address.
  Attributes: the message text. Exists only for the duration of the request
  — nothing is persisted or stored.
- **Chat Reply**: The streamed response sent back for a Chat Request.
  Attributes: the placeholder reply content. Not persisted, not associated
  with any conversation history in this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A client sending a valid message begins receiving a streamed
  reply within 1 second.
- **SC-002**: 100% of valid requests in testing receive a complete streamed
  reply with a clear end-of-stream signal, with no dropped or hanging
  connections.
- **SC-003**: 100% of requests with an empty or whitespace-only message are
  rejected without producing a placeholder reply, verified through testing.
- **SC-004**: A client can distinguish "the reply is still arriving" from
  "the reply is complete" at every point during the stream, without needing
  to guess based on a timeout.
- **SC-005**: 100% of valid requests in testing receive the placeholder reply
  as more than one discrete streamed event, confirming delivery is
  incremental rather than a single blocking chunk.

## Assumptions

- This feature is backend-only. Wiring the existing frontend chat interface
  (feature 002) to call this address is separate future work, not included
  here.
- The client sends its message in the body of a request to the chat address
  and receives a `text/event-stream` response in return — the established
  pattern for chat-style streamed APIs (rather than a plain browser
  `EventSource`, which cannot send a message body).
- Each request opens a new stream that closes once its placeholder reply has
  been fully sent. There is no persistent, multi-turn connection in this
  feature — a new request is made per message.
- No conversation history or persistence is involved; this is a stateless,
  single-turn placeholder. Real response generation (e.g. connecting this to
  an actual language model) is out of scope for this feature.
- Since no real conversational or regulation-sensitive data flows through
  this address yet, it is reasonable for it to remain unauthenticated for
  now (FR-006) — this will need revisiting before it handles real data, per
  the project constitution's security constraints.
