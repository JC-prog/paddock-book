# Feature Specification: Retrieval-Grounded Chat Answers

**Feature Branch**: `feat/008-add-chatbot`

**Created**: 2026-08-07

**Status**: Draft

**Input**: User description: "Wire the chatbot up to real answers instead of the placeholder reply: when a logged-in staff member sends a message, retrieve the most relevant regulation chunks from the pgvector store (feature 006's ingested content), scoped to the departments their account has access to (feature 007), and generate a grounded answer from them via the project's LLM provider — rather than the fixed \"Hello, this is a test response.\" placeholder. ... if nothing relevant is retrieved, the assistant says so rather than guessing or hallucinating an answer. Requires being logged in; an unauthenticated request is rejected." Guardrails against prompt injection / adversarial manipulation were explicitly descoped from this feature (deferred to a future feature — see Assumptions).

## Clarifications

### Session 2026-08-07

- Q: Should SC-002 be softened to reflect that "say I don't know" is best-effort (via prompting) rather than a guaranteed 100% outcome, given guardrails are out of scope for this feature? → A: Split SC-002 into two criteria — a hard 100% guarantee for the deterministic empty-corpus case, and a softer best-effort expectation for the retrieved-but-irrelevant case.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get a grounded answer to a regulation question (Priority: P1)

As a logged-in team staff member, I want to ask the chat assistant a question about my department's regulations and receive an answer based on the actual ingested regulation text, so that I can trust what I'm reading instead of getting a generic placeholder or a guess.

**Why this priority**: This is the entire value of the feature — the honest "no relevant information" behavior in User Story 2 exists to protect the trustworthiness of this core answer, not to replace it.

**Independent Test**: With a regulation document already ingested (feature 006) for a staff member's department, ask a question whose answer clearly exists in that content, and confirm the response reflects that content rather than the old fixed placeholder string.

**Acceptance Scenarios**:

1. **Given** a staff member is logged in and relevant regulation content has been ingested for their department, **When** they ask a question about that content, **Then** they receive an answer grounded in the ingested text, not the placeholder reply.
2. **Given** a staff member is logged in, **When** they ask a question relevant to a department other than their own, **Then** the answer does not draw on that other department's regulation content.
3. **Given** a request is made without being logged in, **When** it reaches the chat endpoint, **Then** it is rejected rather than producing any answer.

---

### User Story 2 - Get an honest answer when nothing relevant exists (Priority: P2)

As a logged-in team staff member, I want the assistant to tell me when it doesn't have relevant regulation content for my question, so that I never mistake a guess for a real answer.

**Why this priority**: A confident-sounding fabricated answer about FIA regulations is worse than no answer at all — this is what makes the assistant safe to actually rely on, ranked just below the core grounded-answer flow itself.

**Independent Test**: Ask a question with no relevant match in the ingested content (e.g. an empty knowledge base, or an unrelated topic) and confirm the assistant clearly states it doesn't have an answer, without inventing one.

**Acceptance Scenarios**:

1. **Given** no ingested content is relevant to a staff member's question, **When** they ask it, **Then** the assistant clearly states it doesn't have relevant information, rather than answering from general knowledge or guessing.
2. **Given** the assistant has stated it doesn't have relevant information, **When** a reviewer checks the answer, **Then** it contains no fabricated regulation details presented as fact.

---

### Edge Cases

- What happens when the ingested knowledge base is completely empty (no documents ingested yet)? The assistant states it has no relevant information — same behavior as User Story 2, not an error.
- What happens if the LLM provider is unreachable or errors? The staff member sees a clear failure indication (matching the existing frontend failure-state behavior from feature 004) rather than a hung request or a fabricated answer.
- What happens when a staff member's message is empty or whitespace-only? Rejected the same way the existing placeholder chat endpoint already rejects it (feature 003, FR-002) — unchanged by this feature.
- What happens when a staff member asks a question spanning content from multiple documents within their own department? The answer may draw from all of them — department scoping applies per staff member, not per document count.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST reject a chat request from a staff member who is not logged in, rather than generating any answer.
- **FR-002**: The system MUST retrieve regulation content relevant to a staff member's question from the ingested knowledge base (feature 006) before generating an answer.
- **FR-003**: The system MUST restrict retrieved content to the department associated with the requesting staff member's account (feature 007) — content from other departments MUST NOT be retrieved for their questions.
- **FR-004**: The system MUST generate the chat answer from the retrieved content, replacing the fixed placeholder reply used previously (feature 003).
- **FR-005**: When the requesting staff member's department has no ingested content at all, the system MUST deterministically respond that it doesn't have relevant information, without attempting to generate a guess.
- **FR-006**: The generated answer MUST NOT include regulation content from a department outside the requesting staff member's access — a direct consequence of FR-003's retrieval scoping, not a separate adversarial defense.
- **FR-007**: The frontend MUST attach the logged-in staff member's session to each chat request, so that a logged-in user's questions actually reach the endpoint as authenticated requests.
- **FR-008**: When content is retrieved but doesn't actually answer the question, the system SHOULD respond by stating it doesn't have relevant information rather than guessing — this is a best-effort behavior of the underlying model following its instructions, not a guaranteed outcome, since guardrails against unreliable model behavior are explicitly out of scope for this feature (see Assumptions).

### Key Entities

- **Chat Question**: A staff member's message, now processed with their identity and department (from feature 007) attached, rather than anonymously.
- **Retrieved Context**: The regulation chunks (feature 006) selected as relevant to a given question, scoped to the requesting staff member's department.
- **Chat Answer**: The generated response — either grounded in retrieved context, or an explicit "no relevant information" response when nothing qualifies.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A logged-in staff member asking about content that has been ingested for their department receives an answer reflecting that content, not the old placeholder reply.
- **SC-002**: 100% of questions asked when the requester's department has zero ingested content result in an explicit "no relevant information" response, with zero fabricated regulation details — deterministic and fully verified through testing (FR-005).
- **SC-003**: When content is retrieved but doesn't answer the question, the assistant is expected to state it doesn't have relevant information rather than fabricate one — a best-effort outcome of the model's instruction-following, not a guaranteed one, since guardrails are out of scope (FR-008). Not held to a 100% pass rate in testing.
- **SC-004**: 100% of chat requests from unauthenticated users are rejected, verified through testing.
- **SC-005**: 100% of tested cross-department retrieval attempts return zero content from outside the requesting staff member's department, verified through testing.
- **SC-006**: A staff member receives a response to a typical question within a short, predictable wait, with a clear failure indication if it doesn't arrive.

## Assumptions

- **Guardrails against prompt injection and adversarial manipulation are explicitly out of scope for this feature** — descoped by the user to prototype the core grounded-answer flow first. This version's only protection against cross-department leakage is retrieval-level filtering (FR-003/FR-006), not defense against a determined attacker trying to manipulate the model into ignoring that filtering at the generation step. Prompt-injection defense is deferred to a future feature.
- The specific LLM provider (and whether it differs between local development and production) is an implementation decision for `/speckit-plan`, not a scope decision for this spec.
- Answers may cite or reference which ingested document(s) they drew from, since this is a regulation-lookup tool where traceability to source text is valuable — the exact citation format is an implementation detail for planning, not a scope decision here.
- This feature updates the existing frontend chat flow (`features/chat/`) to send the logged-in staff member's credentials with each request; it does not introduce a new chat UI.
- Multi-turn conversation memory, fine-tuning/training a custom model, streaming intermediate "thinking" steps, and an admin UI for reviewing flagged messages are all out of scope for this first version (per the input description).
- This feature does not change how documents are ingested (feature 006) or how accounts/departments are assigned (feature 007) — it only consumes both.
