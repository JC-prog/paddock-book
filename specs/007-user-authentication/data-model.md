# Phase 1 Data Model: JWT-Based Authentication System

Two new tables join feature 005's existing `documents`/`document_chunks`
schema in the same local Postgres database. Both reuse the `department`
enum feature 005 already defined (`CREATE TYPE department AS ENUM
('sporting', 'technical', 'financial')`) — no new enum type is introduced.

## User (`users` table)

| Field | Type | Description | Source requirement |
|---|---|---|---|
| `id` | uuid, PK, default `gen_random_uuid()` | Identity, referenced by `refresh_tokens` | — |
| `email` | text, UNIQUE, NOT NULL | Login identity | FR-001, FR-008 |
| `password_hash` | text, NOT NULL | bcrypt hash — never the raw password | FR-004 |
| `department` | `department` enum, NOT NULL | Sporting/Technical/Financial, set once at registration | FR-006 |
| `created_at` | timestamptz, NOT NULL, default `now()` | — | — |

**Validation rules**: `email` MUST be unique (FR-008) and non-empty;
`password_hash` is never written from a raw value shorter than 1 character
(FR-012 — empty passwords are rejected before hashing, no other complexity
rule applies); `department` MUST be one of the three enum values.

**Lifecycle**: Created once at registration (User Story 3). No update path
in this feature — department reassignment and account
deactivation/removal are both out of scope (spec.md Assumptions).

## Refresh Session (`refresh_tokens` table)

| Field | Type | Description | Source requirement |
|---|---|---|---|
| `id` | uuid, PK, default `gen_random_uuid()` | — | — |
| `user_id` | uuid, NOT NULL, FK → `users(id)` | Which account this session belongs to | — |
| `token_hash` | text, UNIQUE, NOT NULL | Hash of the refresh token — the raw token is never stored, mirroring password storage (FR-004's spirit applied to sessions) | FR-003, research.md |
| `created_at` | timestamptz, NOT NULL, default `now()` | — | — |
| `expires_at` | timestamptz, NOT NULL | 7 days from creation (research.md) | — |
| `revoked_at` | timestamptz, NULL | Set on logout or on rotation (research.md); a NULL, non-expired row is the only kind that's valid for a refresh | FR-003 |

**Validation rules**: A refresh attempt is only honored if the matching row
has `revoked_at IS NULL` and `expires_at > now()`. Every successful refresh
sets the old row's `revoked_at` and inserts a new row (rotation,
research.md) rather than updating the token in place.

**Lifecycle**: Created at login or registration (one row per active
session/device — FR allows multiple simultaneous sessions per account, see
spec.md Edge Cases). Revoked explicitly at logout, or implicitly replaced
at each refresh (rotation). Naturally stops being valid once `expires_at`
passes, even if never explicitly revoked.

## Relationships

- `refresh_tokens.user_id` → `users.id`, `ON DELETE CASCADE` (unlike
  feature 005's `documents`/`document_chunks` FK, there's no reason to
  require sessions to be manually cleaned up before a user record could be
  removed — though account removal is itself out of scope for this
  feature, this keeps the constraint correct for whenever it's added).
