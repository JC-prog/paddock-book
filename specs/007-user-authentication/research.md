# Phase 0 Research: JWT-Based Authentication System

No `NEEDS CLARIFICATION` markers remain in the Technical Context. Both
spec-level clarifications from `/speckit-clarify` (account-creation model,
password requirements) were resolved in spec.md. This document records the
supporting technical decisions needed to execute the plan.

## Decision: `PyJWT` 2.13.0 for JWT encode/decode, HS256 signing

- **Rationale**: `PyJWT` is the standard, minimal library for exactly what's
  needed here — signing and verifying JWTs. HS256 (a single shared secret)
  is sufficient because only this one backend service issues and verifies
  tokens today; there's no second service that needs to verify a token
  independently without holding the signing secret, which is the scenario
  RS256's asymmetric keys exist to solve. If a second service needs to
  verify tokens later without trusting it with the signing secret, that's a
  clean, isolated switch to RS256 at that point — not a reason to add the
  complexity now.
- **Alternatives considered**: `python-jose` — broader JOSE/JWE support
  (encryption, more algorithms) that this feature doesn't need;
  `authlib` — a much larger library aimed at building OAuth2/OIDC providers
  and clients, far more surface area than a self-contained JWT
  issue/verify flow requires.

## Decision: `bcrypt` 5.0.0 directly for password hashing

- **Rationale**: A modern, adaptive hashing algorithm, per the constitution's
  explicit requirement. Using the `bcrypt` package directly (rather than
  through `passlib`) avoids depending on a wrapper library that has seen
  materially less maintenance activity in recent years; `bcrypt` itself is
  actively maintained and is what `passlib`'s bcrypt backend calls anyway.
- **Alternatives considered**: `argon2-cffi` (Argon2id) — also a reasonable,
  modern choice per the constitution's "bcrypt or argon2" language; not
  chosen only because `bcrypt` is more ubiquitous and has fewer native
  build-toolchain surprises across platforms. Either would satisfy FR-004;
  this is a defensible, not uniquely-correct, choice.

## Decision: server-tracked refresh tokens with rotation; short-lived access token held in memory only

- **Rationale**: FR-003 requires that logout actually revoke a session, not
  just wait for expiry — a purely stateless JWT scheme can't do that, since
  a token is valid until it expires no matter what the server does. So the
  refresh token is tracked server-side (`refresh_tokens` table): logout
  deletes/revokes the specific row, immediately invalidating that session.
  On every use, the refresh token is rotated (the old row is revoked, a new
  one is issued) — a standard mitigation against a leaked refresh token
  being replayed indefinitely. The access token itself stays a short-lived,
  stateless JWT (cheap to verify on every request, no DB lookup needed) —
  its short lifetime bounds how long a leaked access token remains useful.
  The access token is returned in the response body and held only in the
  Angular app's in-memory state (never `localStorage`/`sessionStorage`), so
  a successful XSS can't read a long-lived credential out of persistent
  browser storage; FR-005's "persists across reloads" requirement is met by
  silently exchanging the httpOnly refresh cookie for a new access token on
  app load, not by persisting the access token itself.
- **Alternatives considered**: Pure stateless JWT (no server-side tracking)
  — rejected outright, since it cannot satisfy FR-003's real-revocation
  requirement. Storing the access token in `localStorage` — rejected as the
  more XSS-exposed option for no real benefit over the in-memory approach,
  given a silent-refresh-on-load flow covers the same "stay logged in
  after reload" UX.

## Decision: refresh token delivered as an httpOnly, Secure, SameSite=Lax cookie; `SameSite=Lax` as the CSRF defense (no separate CSRF-token scheme)

- **Rationale**: An httpOnly cookie is unreadable by JavaScript, so the
  long-lived refresh token is never exposed to an XSS payload the way a
  `localStorage`-held token would be. This works cross-origin here because
  the existing CORS config (`backend/src/main.py`) already lists an
  explicit frontend origin rather than a wildcard — required for
  `Access-Control-Allow-Credentials` to be legal — so `allow_credentials`
  can simply be added to it. `SameSite=Lax` already blocks the cross-site
  POST requests that would otherwise enable a CSRF attack against
  `/v1/auth/refresh` and `/v1/auth/logout` in all modern browsers, without
  needing a hand-rolled double-submit CSRF token scheme.
- **Alternatives considered**: A double-submit CSRF token — more defense in
  depth, but real added complexity (a new header/cookie pair, frontend
  wiring to read and resend it) with no concrete threat this feature
  currently needs to cover beyond what `SameSite=Lax` already provides;
  revisit if a future security review calls for it specifically, rather
  than building it speculatively now (Constitution Principle IV).

## Decision: `users`/`refresh_tokens` join the existing `public` schema; no schema-per-domain split

- **Rationale**: Same database as `documents`/`document_chunks` (feature
  005) — one Postgres container, one `DATABASE_URL`, no new operational
  surface. Matches the existing convention: feature 005's tables aren't in
  a named schema either, so introducing one now for auth alone would be an
  inconsistent, one-off pattern rather than an established project
  convention.
- **Alternatives considered**: A dedicated `auth` schema — cheap, cleaner
  logical separation, and a real option if this project starts using
  schema-per-domain consistently; not adopted here since it would be the
  first and only feature to do so, and Constitution Principle IV disfavors
  introducing a pattern for one module in isolation.

## Decision: schema evolution via a second init file (`002_auth_schema.sql`), applied manually to already-initialized local databases

- **Rationale**: Feature 005 deliberately chose no migration framework —
  `docker-entrypoint-initdb.d` scripts only run on a container's *first*
  startup against an empty data volume. Anyone with an already-running
  local database (every branch after feature 005) won't get
  `002_auth_schema.sql` automatically; quickstart.md documents applying it
  by hand via `psql` against a running container, which avoids the
  destructive alternative (wiping the volume and losing any already-ingested
  regulation data from feature 006). This is the first time that
  no-migration-framework decision has a concrete, visible cost — worth
  naming plainly rather than glossing over.
- **Alternatives considered**: Adopting a migration tool (e.g. Alembic) now
  — would solve this permanently, but is a real scope expansion for an
  auth feature to carry, and feature 005 explicitly deferred that decision
  until it was actually needed; this is a reasonable point to reconsider
  it, but not one this feature should decide unilaterally.

## Decision: access token TTL 15 minutes; refresh token TTL 7 days

- **Rationale**: Conventional, reasonable starting defaults for a web
  session — long enough that a staff member isn't silently logged out
  mid-task (refresh happens transparently), short enough on the access
  token that a leaked one has a narrow window of use. Per spec.md's
  Assumptions, the exact numbers are an implementation detail, not a scope
  decision — easy to tune later without changing the design.
- **Alternatives considered**: None seriously — these are standard,
  low-risk defaults; not worth the design effort of evaluating alternatives
  for a value that's explicitly tunable.
