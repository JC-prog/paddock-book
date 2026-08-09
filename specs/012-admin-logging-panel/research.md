# Research: Admin Logging Panel

## Where `is_admin` lives, and its staleness caveat

**Decision**: `users.is_admin boolean not null default false` (new
column via `db/init/003_admin_settings.sql`), embedded as a JWT claim
alongside the existing `department` claim, following feature 007's
existing pattern exactly (`create_access_token`/`decode_access_token` in
`core/security.py`).

**Rationale**: Matches how `department`-based authorization already
works — no extra DB round-trip needed to check admin status on every
request, consistent with this codebase's existing access-control
mechanism.

**Known, accepted staleness**: if an account is promoted to admin while
already logged in, its *current* access token won't reflect that until
the token naturally refreshes (`refresh_access_token()` already re-fetches
the user row from the DB, so the next refresh — within the existing
7-day refresh-token lifetime — picks up the new claim) or the account
logs in again. Spec.md does not require immediate reflection for an
already-active session, so this is accepted as-is, not solved with new
mechanism (e.g. token revocation on promotion) that wasn't asked for.

## Where the log-destination setting lives

**Decision**: A new single-row Postgres table,
`app_settings (id smallint primary key default 1 check (id = 1),
log_to_file boolean not null default true)`. `modules/admin/repository.py`
owns the real read/write API used by the admin endpoints
(`get_log_destination_setting`, `set_log_destination_setting` — an
upsert, since the row may not exist yet on a fresh install).

**Rationale**: This app already uses Postgres for every other piece of
durable state (accounts, refresh tokens, documents); a table is
consistent with that rather than introducing a second durable-storage
mechanism (e.g. a JSON file) for one boolean. The `CHECK (id = 1)`
keeps it honestly a single-row table rather than an unbounded settings
list, matching spec.md's explicit "not a general settings framework"
boundary.

**Alternatives considered**: Storing it back in `.env` — rejected; a
running application rewriting its own env file is fragile and unusual,
and doesn't naturally support "who changed it and when" (FR-010) the way
a DB row + a log event does.

## How `configure_logging()` learns the DB-backed value without breaking CI

**Decision**: `configure_logging()` gains one new optional parameter,
`db_log_to_file_factory: Callable[[], bool | None] | None = None`,
defaulting to `None` (fully backward compatible with feature 010/011's
existing behavior and tests — nothing changes unless a caller opts in).
When provided, it's called inside the same kind of `try/except Exception`
already used for `settings_factory()` (feature 011); on success with a
non-`None` result, that value overrides `Settings.log_to_file`; on
failure or `None`, the existing `.env`-based default is used, silently
(no warning — this is the documented, expected fallback path for "no
row yet," not a failure condition the operator needs to see, unlike the
`settings_factory()`/file-handler failures which already warn).
`main.py` wires in the real factory — a small function that opens its
own short-lived `psycopg` connection, queries `app_settings`, and closes
it.

**Rationale**: `configure_logging()` runs at import time in `main.py`.
This project's CI (`ci.yml`) runs backend unit tests with no Postgres
service at all — confirmed by reading the workflow file directly, not
assumed. A required DB round-trip at import time would break CI exactly
the way the unprotected `Settings()` call did before feature 011's fix
(see that feature's research.md). Making it optional-and-guarded, rather
than mandatory, avoids repeating that regression class a third time.

**Alternatives considered**: Requiring the DB check unconditionally —
rejected outright given the above. A background/lazy refresh instead of
a startup check — rejected as unnecessary complexity; spec.md (FR-006)
explicitly says a restart is an acceptable and expected way for the
change to take effect, so a one-time startup read is sufficient.

## Why `core/logging.py` doesn't import `modules/admin/repository.py`

**Decision**: `core/logging.py`'s startup query is its own small,
private, read-only function — a duplicate of (a subset of)
`modules/admin/repository.py`'s `get_log_destination_setting`, not a
shared import.

**Rationale**: `core/` is meant to be the dependency-free foundation
`modules/` builds on (per the constitution's stated modular-monolith
architecture — modules can be "extracted into a standalone service later
without restructuring," which requires `core/` not knowing about any
specific module). `core/logging.py` importing from `modules/admin/`
would invert that direction. The duplicated query is one `SELECT`
statement — a small, deliberate, and bounded cost for keeping the
layering clean, not a slippery-slope risk.

**Alternatives considered**: Moving the shared query into `core/db.py`
or a new `core/settings_store.py` so both `core/logging.py` and
`modules/admin/repository.py` call the same function — considered, but
`modules/admin/repository.py`'s version also needs the *write* side
(`set_log_destination_setting`) and the upsert-on-missing-row logic,
which `core/logging.py` doesn't need at all (it only ever reads). Sharing
would mean `core/` carrying admin-specific write logic it never uses,
which is a worse coupling than the small read-only duplication chosen
instead.

## Audit events

**Decision**: Two new event kinds, following feature 010's existing
`contracts/log-schema.md` event-record shape exactly (common envelope +
`event` + relevant fields):

- `log_destination_changed` — emitted from `modules/admin/service.py`
  when a change succeeds: `admin_user_id`, `new_value`.
- `admin_granted` — emitted from `modules/admin/service.py` when a
  promotion succeeds: `promoted_user_id`, `promoted_email`.

**Rationale**: Directly satisfies FR-010/FR-011 (from this spec's two
`/speckit-clarify` rounds) using infrastructure feature 010 already
built — no new logging mechanism needed, just two new call sites.

**CLI needs `configure_logging()` too**: unlike the existing
`modules/ingestion/cli.py` and `modules/download/cli.py` (both predate
feature 010 and never call `configure_logging()`), `modules/admin/cli.py`
calls it at the start of `main()` — otherwise its `admin_granted` event
would have nowhere configured to go. This is the first CLI in the
project to do so; worth calling out as a new, deliberate precedent
rather than an oversight in the older CLIs (they simply predate having
anything to log).

## Migration application to an existing local dev database

**Decision**: `db/init/003_admin_settings.sql` is documented in
`quickstart.md` as requiring either a fresh Postgres volume
(`docker compose down -v && docker compose up -d`) or manually running
its statements against an already-initialized local database.

**Rationale**: `docker-entrypoint-initdb.d` scripts (which is how
`db/init/*.sql` gets applied) only run once, against a brand-new,
empty data volume — confirmed by this project's own Docker Postgres
setup. Anyone with an existing local dev database (i.e. everyone who's
been working on this repo) won't get this migration automatically. This
is the first time this repo has added a schema file after initial setup
existed in practice, so it's worth stating explicitly rather than
assuming it's obvious.
