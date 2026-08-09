# Data Model: Admin Logging Panel

## User Account (existing, feature 007 — this feature adds one field)

| Field | Type | Notes |
|---|---|---|
| `is_admin` | `bool` | **NEW**. Defaults to `false` for every existing and new account. Embedded as a JWT claim, same as `department` (see research.md's staleness caveat). |

## Log Destination Setting (new — `app_settings` table)

A genuine single row, not a general key-value store (spec.md's explicit
boundary).

| Field | Type | Notes |
|---|---|---|
| `id` | `smallint` | Always `1` — `CHECK (id = 1)` enforces there is only ever one row. |
| `log_to_file` | `bool` | Default `true`. Mirrors `Settings.log_to_file`'s meaning (feature 011) — `true` = also write to a local rotating file, `false` = stdout only. |

**Absence is meaningful**: if no row exists yet (fresh install, panel
never used), `configure_logging()` falls back to the existing
`.env`-based `Settings.log_to_file` default — this is not an error
state (spec.md Edge Cases).

## Log Destination Changed Event (new — extends feature 010's log schema)

Emitted by `modules/admin/service.py` on a successful setting change
(FR-010), using the same common envelope as every other event in
`specs/010-app-logging/contracts/log-schema.md`:

| Field | Type | Notes |
|---|---|---|
| `event` | `str` | Always `log_destination_changed`. |
| `admin_user_id` | `str` | The admin account that made the change. |
| `new_value` | `bool` | The value it was changed to. |

## Admin Granted Event (new — extends feature 010's log schema)

Emitted by `modules/admin/service.py` (called from
`modules/admin/cli.py`) on a successful promotion (FR-011):

| Field | Type | Notes |
|---|---|---|
| `event` | `str` | Always `admin_granted`. |
| `promoted_user_id` | `str` | The account that was promoted. |
| `promoted_email` | `str` | Its email, for a human reading the log without a DB lookup. |

## Relationships

- `Log Destination Setting` has no foreign key to `User Account` — who
  changed it is captured in the `Log Destination Changed Event` (a log
  line), not as a column on the settings row itself, per spec.md's
  framing of this as an audited *event*, not a tracked field.
- `Admin Granted Event` doesn't record *which* admin ran the promotion,
  because the promotion path (FR-007) is a CLI run by an operator with
  direct server access, not an authenticated in-app admin action — there
  is no admin session to attribute it to. This is consistent with FR-009
  (no in-app way to grant admin access at all).
