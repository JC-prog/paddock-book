# Phase 0 Research: Chat API with Streamed Responses

No `NEEDS CLARIFICATION` markers remain in the Technical Context. This
document records the supporting technical decisions needed to execute the
plan.

## Decision: `sse-starlette` for SSE framing, pinned to 2.4.1

- **Rationale**: FastAPI's built-in `StreamingResponse` can emit
  `text/event-stream` bytes, but correctly framing each event (`data: ...\n\n`,
  optional `event:`/`id:` fields) and detecting client disconnects
  (`request.is_disconnected()`) is boilerplate `sse-starlette` already
  solves — it's the de facto standard SSE library in the FastAPI ecosystem.
  Using it directly satisfies FR-005 (signal completion) and the disconnect
  edge case (Acceptance Scenario 5) without hand-rolling wire-format details
  that are easy to get subtly wrong. The latest published version (3.4.6,
  verified via `pip index versions sse-starlette`) requires
  `starlette>=0.49.1`, which conflicts with `fastapi==0.115.6`'s pinned
  `starlette<0.42.0,>=0.40.0` — installing it broke `pip check`. 2.4.1 has no
  hard `starlette` version pin (only `anyio>=4.7.0`), so it works with the
  `starlette` version FastAPI already requires, confirmed via a clean `pip
  check` after installing it.
- **Alternatives considered**: Hand-rolled `StreamingResponse` with manual
  `data: ...\n\n` string formatting — more control, but reinvents a solved
  problem and risks framing bugs (e.g. missing blank-line terminators) that
  `sse-starlette` already handles, against Constitution Principle IV (avoid
  unnecessary hand-rolled complexity).

## Decision: word-by-word delivery via an async generator, with a 150ms delay between words

- **Rationale**: FR-004 requires the placeholder ("Hello, this is a test
  response.") to arrive as multiple discrete events, one word at a time.
  **Revised post-launch** (2026-08-05): the initial version used a plain
  sync generator with no delay between words — technically multiple SSE
  events, but arriving fast enough (sub-millisecond) that the streaming was
  imperceptible to a human watching it (e.g. in Postman or the frontend
  UI), which defeated the purpose of having built SSE in the first place.
  Changed to an `async def` generator using `await asyncio.sleep(0.15)`
  between words (not before the first, so SC-001's time-to-first-event
  bound is unaffected) — a synchronous `time.sleep` was not an option since
  it would block the event loop for other requests. `EventSourceResponse`
  already accepts async iterables, so no change was needed in `router.py`.
- **Alternatives considered**: No delay (original decision) — rejected once
  it became clear the streaming effect wasn't actually observable in
  practice. A longer delay (e.g. 300ms+) — rejected as unnecessarily slowing
  down the existing full-stream test in `test_chat.py` for no added
  demonstration value; 150ms is enough to be visible without being sluggish.

## Decision: test the stream with `httpx`'s streaming client, not FastAPI's buffering `TestClient` calls

- **Rationale**: FastAPI's `TestClient` is an `httpx.Client` under the hood
  and supports `with client.stream("POST", url, json=...) as response:
  for chunk in response.iter_lines(): ...`, which reads the SSE response
  incrementally rather than waiting for the full body — necessary to assert
  "more than one discrete event was received" (SC-005) rather than just
  inspecting a final buffered string. This keeps the test a true unit test
  (Constitution Principle II) with no real network hop, same as feature
  001's `TestClient` usage.
- **Alternatives considered**: Calling `client.post(...)` and inspecting
  `response.text` — this buffers the whole stream first, which can still
  assert the final concatenated content is correct but cannot verify that
  delivery was actually incremental (multiple events), the exact behavior
  SC-005 requires testing.

## Decision: request body is JSON `{"message": string}`, not SSE-only `EventSource`

- **Rationale**: Already decided in spec.md Assumptions — the browser-native
  `EventSource` API can only issue GET requests with no body, which can't
  carry an arbitrary chat message. A `POST` with a JSON body and a streamed
  `text/event-stream` response is the established pattern for chat-style
  streaming APIs (matches how most LLM chat APIs stream replies) and is what
  a future frontend client would use via `fetch` + manual stream reading, not
  `EventSource`.
- **Alternatives considered**: None — this was a settled assumption from
  `/speckit-specify`, restated here because it directly shapes the contract
  in `contracts/chat-api.md`.
