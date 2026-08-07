# Quickstart: Retrieval-Grounded Chat Answers

Validates the feature end-to-end per the user stories in
[spec.md](./spec.md). API contract: [contracts/chat-api.md](./contracts/chat-api.md).

## Prerequisites

- The local database running (feature 005), with at least one document
  ingested (feature 006) for a known department
- A registered account (feature 007) in that same department
- [Ollama](https://ollama.com) installed and running locally
  (`ollama serve`, or the desktop app), with the configured model pulled:
  `ollama pull llama3.2` (or whichever model `OLLAMA_MODEL` is set to)
- `backend/.venv` set up with this feature's new dependency installed

## 1. Install the new backend dependency

```bash
cd backend && source .venv/bin/activate && pip install -r requirements.txt
```

## 2. Confirm Ollama is reachable

```bash
curl -s http://localhost:11434/api/tags
```

**Expected**: a JSON list including the model you pulled. If this fails,
the chat request in step 4 will fail with a clear LLM-provider-error
indication (contracts/chat-api.md) rather than hanging.

## 3. Register and log in (feature 007), get an access token

```bash
curl -s -c cookies.txt -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"quickstart@example.com","password":"a-real-password","department":"sporting"}' \
  | tee /tmp/register.json
ACCESS_TOKEN=$(python3 -c "import json; print(json.load(open('/tmp/register.json'))['access_token'])")
```

(Skip straight to `/v1/auth/login` instead if the account already exists.)

## 4. Ask a question about content ingested for that department (User Story 1)

```bash
curl -N -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"message":"Summarize the key point of the regulation I just ingested."}'
```

**Expected**: an SSE stream (`-N` disables curl's buffering so you see it
arrive incrementally) of `data:` lines whose combined text reflects the
ingested content — not the old fixed placeholder string.

## 5. Ask an unrelated question (User Story 2)

```bash
curl -N -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"message":"What is the capital of France?"}'
```

**Expected**: a clear "I don't have relevant information" reply — not a
guess, not a real answer to the unrelated question.

## 6. Verify an unauthenticated request is rejected

```bash
curl -i -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"anything"}'
```

**Expected**: `401`, no SSE stream opened.

## 7. Verify department scoping

Using an account in a *different* department than the ingested document
(register a second account with a different `department` value), repeat
step 4's question. **Expected**: the answer does not reflect the other
department's content — either a "no relevant information" reply, or an
answer that doesn't include that content, depending on what (if anything)
exists for the second account's own department.

## 8. Frontend: full journey in the browser

- Log in at `http://localhost:4200/login`.
- Ask a question on the chat page — confirm the answer streams in
  progressively (same UX as the placeholder did) and reflects real ingested
  content.
- Log out, then attempt to reach the chat page directly — confirm the
  existing route guard (feature 007) still redirects to `/login` before any
  chat request is even attempted.

## 9. Run the automated tests

```bash
# Unit tests (generation, service — no live dependencies; Ollama is mocked)
cd backend && source .venv/bin/activate && pytest tests/unit

# Integration test (retrieval — requires the local database running)
./scripts/test-backend-integration.sh

# Frontend
cd frontend && npm test
```

**Expected**: all pass, including the department-scoping and empty-corpus
retrieval tests against the real database.

## 10. Clean up the quickstart account

```bash
docker compose exec -T db psql -U paddockbook -d paddockbook -c \
  "DELETE FROM refresh_tokens WHERE user_id = (SELECT id FROM users WHERE email = 'quickstart@example.com');"
docker compose exec -T db psql -U paddockbook -d paddockbook -c \
  "DELETE FROM users WHERE email = 'quickstart@example.com';"
```
