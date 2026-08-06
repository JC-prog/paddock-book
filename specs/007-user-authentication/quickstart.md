# Quickstart: JWT-Based Authentication System

Validates the feature end-to-end per the user stories in
[spec.md](./spec.md). API contract: [contracts/auth-api.md](./contracts/auth-api.md).
Data shapes: [data-model.md](./data-model.md).

## Prerequisites

- The local database running (feature 005: `docker compose up -d`)
- `backend/.venv` set up with this feature's new dependencies installed
- `frontend/` dependencies installed (`npm install`)

## 1. Apply the new schema to an already-running database

Feature 005's `docker-entrypoint-initdb.d` scripts only run on a
container's *first* startup (research.md) — if your local database was
created before this feature, `002_auth_schema.sql` won't have run
automatically. Apply it by hand, without losing any existing data:

```bash
docker compose exec -T db psql -U paddockbook -d paddockbook < db/init/002_auth_schema.sql
```

(A fresh `docker compose up -d` against a brand-new volume picks up both
init files automatically — this step is only needed for a database that
already existed before this feature.)

## 2. Install the new backend dependency and start the servers

```bash
cd backend && source .venv/bin/activate && pip install -r requirements.txt
./scripts/dev-setup.sh  # or start backend/frontend however you normally do
```

## 3. Register a new account (User Story 3, Acceptance Scenarios 1–3)

```bash
curl -i -c cookies.txt -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"quickstart@example.com","password":"a-password","department":"sporting"}'
```

**Expected**: `201`, a JSON body with `access_token` and `user`, and a
`Set-Cookie: refresh_token=...` header (saved to `cookies.txt`). Repeating
the same request again:

```bash
curl -i -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"quickstart@example.com","password":"a-password","department":"sporting"}'
```

**Expected**: `422` — duplicate email rejected, no second account created.

## 4. Log in (User Story 1)

```bash
curl -i -c cookies.txt -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"quickstart@example.com","password":"a-password"}'
```

**Expected**: `200`, `access_token` in the body. Then with a wrong password:

```bash
curl -i -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"quickstart@example.com","password":"wrong"}'
```

**Expected**: `401` with a generic error — same shape whether the password
is wrong or the email doesn't exist at all (verify by trying a nonexistent
email too).

## 5. Refresh and log out (User Story 2)

```bash
curl -i -b cookies.txt -c cookies.txt -X POST http://localhost:8000/v1/auth/refresh
curl -i -b cookies.txt -X POST http://localhost:8000/v1/auth/logout
```

**Expected**: `refresh` returns `200` with a new `access_token` and a
rotated cookie; `logout` returns `204`. Then confirm the session is really
gone:

```bash
curl -i -b cookies.txt -X POST http://localhost:8000/v1/auth/refresh
```

**Expected**: `401` — the logged-out refresh token no longer works.

## 6. Frontend: full journey in the browser

- Visit `http://localhost:4200/register`, submit the form — confirm you land
  logged in, and the navbar reflects your account.
- Reload the page — confirm you're still logged in (FR-005, silent refresh
  on load).
- Click logout — confirm you're routed away from any page that requires
  login, and reloading no longer restores a session.
- Visit `http://localhost:4200/login` with the account created above —
  confirm login works, and that an unauthenticated visit to a guarded route
  (e.g. the chat page) redirects to `/login`.

## 7. Run the automated tests

```bash
# Unit tests (security, service — no live dependencies)
cd backend && source .venv/bin/activate && pytest tests/unit

# Integration tests (repository, full API flow — requires the local database running)
./scripts/test-backend-integration.sh

# Frontend
cd frontend && npm test
```

**Expected**: all pass, including the full register→login→refresh→logout
flow against a real database, and the frontend guard/interceptor/component
tests.

## 8. Clean up the quickstart account

```bash
docker compose exec -T db psql -U paddockbook -d paddockbook -c \
  "DELETE FROM refresh_tokens WHERE user_id = (SELECT id FROM users WHERE email = 'quickstart@example.com');"
docker compose exec -T db psql -U paddockbook -d paddockbook -c \
  "DELETE FROM users WHERE email = 'quickstart@example.com';"
```

(`refresh_tokens` rows first — same FK-ordering reasoning as feature 006's
`document_chunks`/`documents` cleanup, since a manual FK check applies here
too even though `ON DELETE CASCADE` is configured; deleting explicitly
either way keeps this step correct regardless.)
