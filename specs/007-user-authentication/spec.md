# Feature Specification: JWT-Based Authentication System

**Feature Branch**: `007-user-authentication`

**Created**: 2026-08-06

**Status**: Draft

**Input**: User description: "Build a authentication system for this app using jwt token. Set up the database for the authentication, then build the backend then wire up the frontend."

## Clarifications

### Session 2026-08-06

- Q: Should account creation be self-service or admin/invite-provisioned? → A: Open self-service — a public "Register" page exists; a new staff member creates their own account and selects their own department at sign-up.
- Q: What minimum requirements should a password meet before the system accepts it during registration? → A: No system-enforced requirement — any non-empty password is accepted.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Log in to access the application (Priority: P1)

As a team staff member, I want to log in with my email and password so that I
can access the application using my own identity, rather than the app being
fully open to anyone.

**Why this priority**: Login is the entry point for every other authenticated
interaction. Without it, nothing else in this feature — or the
department-aware access control the project is building toward — has any
effect.

**Independent Test**: Using an existing account, submit valid credentials and
confirm access is granted; submit invalid credentials and confirm access is
denied with a clear error. Fully verifiable with a single pre-existing test
account, independent of however new accounts get created.

**Acceptance Scenarios**:

1. **Given** a staff member has a valid account, **When** they submit the
   correct email and password, **Then** they are logged in and receive an
   authenticated session.
2. **Given** a staff member submits an incorrect password, **When** they
   attempt to log in, **Then** access is denied with a clear error that does
   not reveal whether the email address itself has an account.
3. **Given** a staff member is already logged in, **When** they reload the
   app or navigate between pages, **Then** they remain logged in without
   re-entering credentials, until they log out or their session expires.

---

### User Story 2 - Log out to end a session securely (Priority: P2)

As a team staff member, I want to log out so that my session is actually
terminated — not just hidden in the browser — since I may be using a shared
or work-provided machine.

**Why this priority**: Without a real logout, a staff member has no way to
revoke their own access on a machine they don't fully control. For a tool
handling confidential regulation content, that's a real security gap, not
just a convenience.

**Independent Test**: Log in, then log out, then confirm the previous
session can no longer be used to perform any authenticated action. Fully
verifiable independent of how the account was created.

**Acceptance Scenarios**:

1. **Given** a staff member is logged in, **When** they log out, **Then**
   their session is invalidated and any further request using it is
   rejected.
2. **Given** a staff member has logged out, **When** they use the browser's
   back button or a cached page, **Then** they cannot perform any
   authenticated action without logging in again.

---

### User Story 3 - Register a new account (Priority: P3)

As a new team staff member, I want to register my own account — providing my
email, a password, and my department — so that I can log in without needing
an admin to set an account up for me.

**Why this priority**: Needed before Login (User Story 1) has anyone to log
in as — but ranked P3 here because Login and Logout can each be verified
independently once at least one account already exists. This story matters
for the ongoing, repeatable process of getting new staff onto the system.

**Independent Test**: Submit the registration form with an email, password,
and department, then confirm the resulting account can immediately log in
with those credentials. Fully verifiable independent of Login/Logout's own
scenarios, once the registration flow itself exists.

**Acceptance Scenarios**:

1. **Given** a new staff member submits the registration form with a valid,
   unused email, a password, and a department, **When** registration
   completes, **Then** a new account exists with that department assigned,
   and no password is stored in a readable or reversible form.
2. **Given** an account already exists for a given email address, **When**
   registration is attempted again for that same email, **Then** it is
   rejected rather than creating a duplicate account.
3. **Given** a new staff member submits the registration form without a
   valid department selection, **When** registration is attempted, **Then**
   it is rejected with a clear error before an account is created.

---

### Edge Cases

- What happens when a staff member's session token expires mid-use? The
  system should refresh it silently if still within a valid renewal window,
  or require the staff member to log in again if it's fully expired or has
  been revoked.
- What happens if someone repeatedly submits the wrong password for the same
  account? The system applies basic protection against rapid repeated
  attempts (see FR-009) rather than allowing unlimited retries.
- What happens if a staff member logs in from two different devices or
  browsers at once? Both sessions are valid independently — this feature
  does not restrict an account to a single active session (see Assumptions).
- What happens if a staff member submits an empty password during
  registration? It is rejected (FR-012) — a non-empty password is the only
  requirement enforced; no minimum length or composition rule applies.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow a staff member with valid credentials
  (email and password) to log in and receive an authenticated session.
- **FR-002**: The system MUST reject a login attempt with incorrect
  credentials, returning a clear error that does not reveal whether the
  submitted email address has an account.
- **FR-003**: The system MUST allow a logged-in staff member to explicitly
  log out, and that logout MUST actually invalidate their session so it
  cannot be used again — not merely rely on the session naturally expiring
  later.
- **FR-004**: The system MUST store passwords using a one-way, non-reversible
  hashing method. Passwords MUST NOT be stored in plaintext or in any
  reversible/encrypted form.
- **FR-005**: A staff member's authenticated session MUST persist across page
  reloads and normal in-app navigation, without requiring them to log in
  again until they log out or their session ends.
- **FR-006**: Every account MUST have exactly one department (Sporting,
  Technical, or Financial) associated with it at the time the account is
  created, matching the department values already used elsewhere in the
  system.
- **FR-007**: The system MUST allow a new staff member to create their own
  account through a public, self-service registration flow — providing an
  email, a password, and selecting their department — without requiring an
  admin or an invitation.
- **FR-008**: The system MUST reject an attempt to create an account using an
  email address that already has an account, rather than creating a
  duplicate.
- **FR-009**: The system MUST apply basic protection against rapid, repeated
  failed login attempts against the same account, rather than allowing
  unlimited immediate retries.
- **FR-010**: The frontend MUST provide a way for a staff member to log in
  and log out through the app's own interface, and MUST reflect their
  current authenticated state (e.g. showing who is logged in when
  authenticated, and requiring login before reaching the rest of the app
  when not).
- **FR-011**: The frontend MUST provide a public registration form where a
  new staff member can submit an email, a password, and select their
  department to create their own account.
- **FR-012**: The system MUST reject registration if the submitted password
  is empty, but MUST NOT enforce any other password complexity or
  composition rule (e.g. minimum length, character mix) in this first
  version.

### Key Entities

- **User Account**: Represents a staff member's identity in the system — an
  email address, a securely-hashed password, and the department (Sporting,
  Technical, or Financial) they belong to. One account per staff member.
- **Session**: Represents an active, logged-in state tied to a User Account.
  Created at login, and MUST be individually revocable so that logout (User
  Story 2) has a real effect rather than relying only on natural expiry.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A staff member with valid credentials can log in and reach the
  application in a single attempt, without retries caused by system error.
- **SC-002**: 100% of logout actions result in that session being unusable
  for any further authenticated action, verified through testing.
- **SC-003**: 100% of login attempts with incorrect credentials are rejected
  without revealing whether the submitted email address has an account,
  verified through testing.
- **SC-004**: 100% of stored passwords are non-reversible, verified through
  testing — no password is ever recoverable in its original form, including
  with direct access to the stored data.
- **SC-005**: Every account has exactly one valid department at all times,
  verified through testing.
- **SC-006**: A staff member's login persists across page reloads and normal
  in-app navigation without needing to re-authenticate, until they log out
  or their session naturally expires.

## Assumptions

- Authentication is self-hosted — no third-party identity provider (e.g. AWS
  Cognito) is used, per the project constitution's Technology & Security
  Constraints. This application owns credential storage and session
  issuance directly.
- Password reset / forgot-password flows are out of scope for this first
  version; a staff member who forgets their password needs manual/
  administrative help for now.
- Multi-factor authentication and OAuth/social login are out of scope.
- This feature gates the app's existing frontend routes (e.g. the chat page)
  behind requiring a logged-in session. The backend's existing endpoints
  (health, chat, ingestion) are not modified to reject unauthenticated
  requests as part of this feature — none of them currently serve
  department-scoped regulation content, so enforcing that at the API layer
  is deferred to when they do, per the constitution's access-control
  principle. This feature does deliver a reusable request-authentication
  mechanism that a future feature can apply to those endpoints.
- Multiple simultaneous sessions per account (e.g. logged in on two devices)
  are allowed; this feature does not restrict an account to a single active
  session.
- The exact threshold/duration for the repeated-failed-login protection
  (FR-009) is an implementation detail to be decided during planning, not a
  scope decision for this specification.
- Account deactivation or removal is out of scope for this first version —
  once created, an account is not deleted or disabled by this feature.
- Department assignment happens once, at account-creation time. This feature
  does not include a way to change an existing account's department
  afterward.
- No email verification/confirmation step is required before a
  self-registered account can log in — registration takes effect
  immediately. Verifying email ownership is out of scope for this first
  version.
