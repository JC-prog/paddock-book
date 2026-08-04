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

## Decision: word-by-word delivery via a generator function, no artificial delay

- **Rationale**: FR-004 requires the placeholder ("Hello, this is a test
  response.") to arrive as multiple discrete events, one word at a time. A
  plain Python generator (`for word in text.split(" "): yield word`) fed into
  `EventSourceResponse` satisfies this with no added complexity. No
  artificial delay is added between words — SC-001 only bounds time-to-first-
  event (under 1 second), and nothing in the spec requires a particular
  pacing between subsequent words; adding one would be speculative for a
  placeholder with no real generation latency to simulate yet.
- **Alternatives considered**: Delaying each word (e.g. `asyncio.sleep(0.1)`)
  to simulate realistic typing pace — rejected as unrequested and untestable
  against any stated success criterion; can be added later if a real
  language-model integration's actual pacing needs demonstrating.

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
