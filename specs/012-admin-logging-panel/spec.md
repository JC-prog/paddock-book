# Feature Specification: Admin Logging Panel

**Feature Branch**: `012-admin-logging-panel`

**Created**: 2026-08-09

**Status**: Draft

**Input**: User description: "Build an admin panel that lets an authorized operator control where backend logs are persisted — toggling between \"also write to a local rotating file\" (feature 011) and \"stdout only\" (which is what the production CloudWatch capture relies on) — without editing the .env file or restarting through a terminal. Access requires a new is_admin flag on the account (default false); nobody without it can see or change this setting. The chosen setting is stored durably (surviving app restarts) and takes effect the next time the backend starts — no live/hot-reload of logging configuration is required. Add a small CLI, mirroring the existing PDF-ingestion CLI's pattern, to promote an existing account to admin (python -m ... --promote-admin <email> style) — there is no self-service or UI-based way to grant admin access. Out of scope: a real, direct CloudWatch SDK integration (this feature only ever toggles between the two destinations feature 011 already built, it does not add a third); a general-purpose settings/configuration framework — this panel controls exactly one setting, not an extensible list; live/hot-reloading a running backend's logging configuration without a restart; any other admin capability beyond this one logging-destination control."

## Clarifications

### Session 2026-08-09

- Q: Should changing the log-destination setting itself be recorded as an audit event, the same way feature 010 already logs login/logout/registration events? → A: Yes — log who changed the setting, to what value, and when, as its own event (matching feature 010's `login_succeeded`-style pattern).
- Q: Should promoting an account to admin access (FR-007/US2) also be recorded as an audit event, the same way the log-destination change now is (FR-010)? → A: Yes — log which account promoted whom, and when, matching FR-010's pattern.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Change where logs are persisted, without touching a terminal (Priority: P1)

As an authorized operator, I want to view and change whether the backend
also writes logs to a local file (on top of stdout) through a panel in
the app, so that I don't need shell access to the server or to edit its
`.env` file to make that change.

**Why this priority**: This is the entire point of the feature — today
this setting can only be changed by editing `.env` directly and
restarting from a terminal, which defeats the purpose of a self-service
admin control.

**Independent Test**: As an account with admin access, open the panel,
confirm it shows the current setting, change it, restart the
application, and confirm the new setting is the one now in effect. As an
account without admin access, confirm the panel and the setting are
completely inaccessible.

**Acceptance Scenarios**:

1. **Given** an authorized admin is logged in, **When** they open the
   panel, **Then** they see the currently active log-destination setting
   (local file + stdout, or stdout only).
2. **Given** an authorized admin changes the setting, **When** the
   backend application is next restarted, **Then** it starts up using the
   newly chosen setting — the change does not need to take effect before
   that restart.
3. **Given** an authorized admin changes the setting, **When** the
   change is recorded, **Then** it names which admin made the change,
   what the new value is, and when it happened — the same way feature
   010 already records login/logout/registration events.
4. **Given** a logged-in account without admin access, **When** they
   attempt to view or change the setting (through the panel or directly
   against its underlying address), **Then** the attempt is rejected.
5. **Given** no one is logged in, **When** a request to view or change
   the setting is made, **Then** it is rejected the same way any other
   unauthenticated request to this application already is.

---

### User Story 2 - Grant an account admin access (Priority: P2)

As an operator with direct access to the running application, I want to
promote an existing account to admin without touching the database
directly, so that granting the first (and any future) admin is a
documented, repeatable action rather than a one-off manual data edit.

**Why this priority**: User Story 1 has no valid actor to test with in a
real deployment until at least one account has admin access — this is
the mechanism that creates that first admin, and every one after it.
Ranked below Story 1 because the panel is the feature's actual value;
this is what makes it usable without ad hoc database access.

**Independent Test**: Run the promotion action against an existing
account's email and confirm that account now has admin access — fully
verifiable independently of the panel itself.

**Acceptance Scenarios**:

1. **Given** an existing account, **When** an operator runs the
   promotion action against its email, **Then** that account has admin
   access from that point on.
2. **Given** an email address with no matching account, **When** an
   operator attempts to promote it, **Then** the action is rejected with
   a clear error, and no account is created or modified.
3. **Given** an account that already has admin access, **When** an
   operator runs the promotion action against it again, **Then** nothing
   breaks — the account simply remains an admin.
4. **Given** an account is successfully promoted to admin, **When** the
   promotion is recorded, **Then** it names which account was promoted
   and when it happened, the same way the log-destination setting change
   (User Story 1) is recorded.

---

### Edge Cases

- What happens if the durably-stored setting doesn't exist yet (e.g. a
  fresh install that has never had the panel used)? The application
  falls back to today's `.env`-based default (feature 011), unchanged.
- What happens if an admin changes the setting but the application is
  never restarted? The previous setting remains in effect until a
  restart happens — this is expected, not an error condition (FR-006).
- What happens if someone without a session at all (not just without
  admin access) hits the setting's address directly? Rejected the same
  way any other unauthenticated request to this application already is,
  not a special case for this feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST add an admin-access flag to accounts,
  defaulting to no admin access for every existing and newly created
  account.
- **FR-002**: The system MUST allow an account with admin access to view
  the currently active log-destination setting.
- **FR-003**: The system MUST allow an account with admin access to
  change the log-destination setting between "also write to a local
  file" and "stdout only."
- **FR-004**: The system MUST reject any attempt to view or change the
  log-destination setting from an account without admin access, or from
  a request with no authenticated account at all.
- **FR-005**: The chosen log-destination setting MUST be stored durably,
  surviving an application restart.
- **FR-006**: A changed log-destination setting MUST take effect the
  next time the backend application starts. It is not required to take
  effect on a running instance without a restart.
- **FR-007**: The system MUST provide a way for an operator to promote
  an existing account to admin access without requiring direct database
  access.
- **FR-008**: The promotion action MUST reject an email address that has
  no matching account, with a clear error, rather than creating one.
- **FR-009**: The system MUST NOT provide any self-service or in-app UI
  way for an account to grant itself, or any other account, admin
  access — the promotion action (FR-007) is the only path to it.
- **FR-010**: The system MUST record a change to the log-destination
  setting as an event — naming which admin made the change, the new
  value, and when — the same way feature 010 already records
  authentication events.
- **FR-011**: The system MUST record a successful promotion to admin
  access (FR-007) as an event — naming which account was promoted and
  when — matching FR-010's pattern.

### Key Entities

- **User Account** (existing, feature 007): gains an admin-access
  attribute, defaulting to off.
- **Log Destination Setting**: the single durable, admin-editable value
  this feature controls — whether the backend also writes logs to a
  local file (feature 011) or stdout only. Not a general settings
  collection; this feature governs exactly this one value.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An admin can view and change the log-destination setting,
  and that change is still the one in effect after the application is
  restarted.
- **SC-002**: 100% of attempts to view or change the log-destination
  setting from a non-admin or unauthenticated request are rejected,
  verified through testing.
- **SC-003**: An operator can grant an existing account admin access
  without direct database access, verified through testing.
- **SC-004**: 100% of promotion attempts against an email with no
  matching account are rejected with a clear error, verified through
  testing.
- **SC-005**: 100% of successful log-destination setting changes produce
  a corresponding recorded event naming the admin, the new value, and
  when it happened, verified through testing.
- **SC-006**: 100% of successful admin-access promotions produce a
  corresponding recorded event naming the promoted account and when it
  happened, verified through testing.

## Assumptions

- "Stdout only" is what lets the existing, already-working AWS
  production log capture (outside this application's own code) do its
  job — this feature does not add a direct CloudWatch SDK integration or
  a third destination option; it only toggles between the two
  destinations feature 011 already built.
- No live/hot-reload of a running backend's logging configuration is in
  scope — a restart is the expected way a changed setting takes effect
  (FR-006), consistent with the explicit direction that this is
  acceptable for now.
- This panel is scoped to exactly one setting. It is not the start of a
  general-purpose admin configuration framework — additional
  admin-controllable settings, if ever needed, are a separate future
  decision, not something this feature should generalize toward
  pre-emptively.
- The first admin account is created by running the promotion action
  (FR-007) against an account that already exists via normal
  self-service registration (feature 007) — this feature does not change
  how accounts are created, only how one gains admin access afterward.
