# Phase 0 Research: Chat Frontend-Backend Integration

No `NEEDS CLARIFICATION` markers remain in the Technical Context — both
clarifications from `/speckit-clarify` were resolved in spec.md. This
document records the supporting technical decisions needed to execute the
plan.

## Decision: `fetch` + manual SSE line parsing, no `EventSource`

- **Rationale**: Already anticipated in feature 003's `research.md` — the
  browser's native `EventSource` API can only issue GET requests with no
  body, which can't carry the chat message. A `fetch` POST with
  `response.body.getReader()` read in a loop, decoding chunks and splitting
  on `data:` lines per `specs/003-chat-api-sse/contracts/chat-api.md`'s wire
  format, is the standard way to consume a POST-based SSE stream.
- **Alternatives considered**: A third-party SSE-over-fetch library — adds a
  dependency for a small amount of line-parsing logic this feature can own
  directly and test thoroughly; rejected as unnecessary given the wire
  format is simple and fixed by our own backend contract.

## Decision: `ChatApiService.streamReply()` returns an RxJS `Observable<string>`

- **Rationale**: Angular's ecosystem already uses RxJS (a project dependency
  since feature 001), and `Observable` semantics map directly onto the SSE
  contract: `next(word)` per event, `complete()` on a clean stream end
  (FR-004), `error()` on a timeout or dropped connection (FR-005). This
  needs no custom discriminated-union type — the `Observable` contract
  already expresses exactly the three outcomes this feature cares about.
  `ChatService` subscribes and reacts to each channel without `ChatApiService`
  knowing anything about the message list.
- **Alternatives considered**: A callback-based API (`onWord`/`onComplete`/
  `onError` functions) — works, but reinvents what `Observable` already
  provides idiomatically in this codebase, and is harder to unit-test
  cleanly (no built-in subscription/teardown semantics).

## Decision: 10-second time-to-first-event timeout via `AbortController`

- **Rationale**: FR-005 requires treating a message as failed if no part of
  its reply arrives within 10 seconds. Implementation: start a
  `setTimeout(() => controller.abort(), 10_000)` when the request begins,
  and `clearTimeout` the moment the first chunk is read from the stream.
  Aborting the `fetch` via `AbortController` causes the pending read to
  reject, which `ChatApiService` translates into `error()` — no separate
  "did we already receive something" flag is needed beyond the timer's own
  clear/not-cleared state. This timeout only guards time-to-first-byte, not
  overall reply duration, per FR-005's exact wording ("no part of a reply
  has arrived within 10 seconds").
- **Alternatives considered**: A single overall request timeout covering the
  whole stream — rejected because a slow-but-actively-streaming reply
  (e.g. a real, longer future response) would be wrongly killed; FR-005 is
  specifically about total silence, not total duration.

## Decision: distinguish a clean stream end from a dropped connection via the reader promise, not word-count

- **Rationale**: `reader.read()` resolving with `{ done: true }` after zero
  or more successful reads means the server closed the stream normally —
  treated as FR-004 (complete). `reader.read()` rejecting (network error,
  aborted mid-read) means the connection dropped — treated as FR-005/Edge
  Case (error, with whatever partial text already arrived left visible per
  FR-006). Counting words against the known placeholder length was
  considered and rejected: it would silently break the moment feature 003's
  placeholder is replaced with a real, variable-length reply.
- **Alternatives considered**: Comparing received content against the known
  fixed placeholder string — tightly couples this feature to feature 003's
  placeholder implementation detail in a way that would need revisiting the
  moment real response generation lands; rejected.

## Decision: the assistant reply bubble is created immediately (empty, `streaming` status), not after the first word

- **Rationale**: Addresses the Edge Case "user should be able to tell a
  reply is expected/in progress." Creating the bubble at send time (rather
  than waiting for the first word) gives an immediate visual acknowledgment
  that a reply is coming, which `MessageBubbleComponent` can render as a
  subtle loading affordance while `status === 'streaming'` and text is
  still empty.
- **Alternatives considered**: Only creating the bubble once the first word
  arrives — simpler, but produces up to ~2 seconds (SC-001) of no feedback
  at all after sending, which is worse UX for no real implementation
  savings.

## Decision: backend CORS widened to allow `POST`, no other CORS change

- **Rationale**: `backend/src/main.py`'s `CORSMiddleware` currently sets
  `allow_methods=["GET"]` (added in feature 001 for the health check only).
  `/v1/chat` needs `POST`. Widening `allow_methods` to `["GET", "POST"]` is
  the minimal change; `allow_origins` already includes the frontend's dev
  origin and needs no change.
- **Alternatives considered**: `allow_methods=["*"]` — broader than needed;
  explicit `["GET", "POST"]` stays consistent with the principle of only
  allowing what's actually used.

## Decision: test `ChatApiService` against a mocked global `fetch` returning a constructed `ReadableStream`

- **Rationale**: `new Response(new ReadableStream({ start(controller) {...} }))` lets
  a test simulate the exact byte chunks the real backend would send —
  including a chunk boundary splitting a `data:` line, and a stream that
  errors mid-read — without any real network call, keeping this a true unit
  test (Constitution Principle II). Node 24 (this project's runtime) provides
  `fetch`/`ReadableStream`/`Response` as global built-ins, so no polyfill is
  needed in the Vitest/jsdom environment.
- **Alternatives considered**: Spinning up a real (or mocked HTTP server)
  test server — heavier, slower, and unnecessary when the fetch/stream APIs
  can be constructed directly in-process.
