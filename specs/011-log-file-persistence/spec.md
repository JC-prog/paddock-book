# Feature Specification: Log File Persistence

**Feature Branch**: `011-log-file-persistence`

**Created**: 2026-08-08

**Status**: Draft

**Input**: User description: "Persist the application's logs to a file on disk, in addition to the existing stdout output added in feature 010. Local development and any environment without a log-collection platform behind it should end up with an actual log file an engineer can open after the fact, not just whatever happened to still be in a terminal's scrollback. Total disk space used for log files must be capped and predictable — old log data rolls over automatically once a size threshold is reached, rather than growing unbounded or requiring someone to manually delete it. A future feature will add an admin panel letting an operator choose where logs go (local file storage vs. CloudWatch) at runtime; this feature doesn't build that panel, but the file-persistence mechanism it adds should be a self-contained option that a future toggle could switch on/off, not something hardcoded to always run. Out of scope: shipping logs to an external service or log aggregator; changing the log content/format itself (that's feature 010's JSON schema, unchanged here); the admin panel and any runtime configuration UI; anything related to the AWS/CloudWatch production path, which already has its own capture mechanism independent of this feature."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open a real log file after the fact (Priority: P1)

As an engineer working locally (or in any environment with no log-collection
platform behind it), I want the application's logs to end up in an actual
file on disk, so that I can open and search them after the fact instead of
depending on whatever's still visible in a terminal's scrollback.

**Why this priority**: This is the entire point of the feature — feature
010 already produces well-structured log lines, but today they only exist
for as long as the process's stdout is being watched. Without a file, a
closed terminal means the logs are simply gone.

**Independent Test**: Run the application, trigger a few requests, then
close the terminal (or otherwise stop watching stdout) and confirm a log
file on disk contains those same log entries, openable and searchable
independently of the running process.

**Acceptance Scenarios**:

1. **Given** the application is running with file persistence enabled,
   **When** a request is handled, **Then** its log entry appears in a file
   on disk, in the same form it would have appeared on stdout.
2. **Given** log entries have already been written to the file, **When**
   the application process later stops, **Then** those entries remain
   readable in the file after the process is gone.
3. **Given** file persistence is not enabled, **When** the application
   runs, **Then** no log file is created — this is a configurable option,
   not something that always runs unconditionally.

---

### User Story 2 - Log files never grow without bound (Priority: P2)

As an engineer or operator responsible for a machine running this
application, I want the total disk space used by log files to stay capped
and predictable, so that logging can never be the reason a disk fills up.

**Why this priority**: Without this, User Story 1's file grows forever —
technically useful, but a real operational hazard over time. This builds
directly on Story 1 (there must be a file before it can be rotated) and
isn't meaningful on its own.

**Independent Test**: Run the application under enough load to exceed the
rotation threshold, then confirm older log data has rolled over
automatically (into a bounded number of older files, or pruned outright)
and total disk usage for log files stays under a fixed, predictable cap —
without anyone manually intervening.

**Acceptance Scenarios**:

1. **Given** the current log file reaches the configured size threshold,
   **When** more log entries are produced, **Then** the file rolls over
   automatically and new entries continue to be written without
   interruption or data loss for the entries already written.
2. **Given** rollover has happened repeatedly over time, **When** the
   total disk usage for log files is checked, **Then** it never exceeds a
   fixed, predictable maximum — old rolled-over data is pruned once that
   maximum is reached, not kept forever.

---

### Edge Cases

- What happens if the log file's directory doesn't exist yet, or the
  process doesn't have permission to write there? File persistence fails
  to start, but this MUST NOT prevent the application itself from starting
  or from continuing to log to stdout (feature 010's existing behavior) —
  a broken file destination is not allowed to take down the app.
- What happens if the disk fills up despite the size cap (e.g. from
  something else entirely)? Per feature 010's existing FR-007, a logging
  failure of any kind — including a failed file write — MUST NOT fail the
  request being handled.
- What happens to log entries written right as a rollover happens? None
  are lost or corrupted — a rollover is a clean cut between the old file
  and the new one, not a truncation mid-write.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST be able to write every log entry it
  produces (per feature 010's existing content/format) to a file on disk,
  in addition to the existing stdout output.
- **FR-002**: File persistence MUST be a configurable option — on or off
  — not something that unconditionally runs regardless of configuration.
  A future feature will let an operator control this at runtime; this
  feature only needs to make it a self-contained, independently
  switchable capability today (e.g. via configuration read at startup),
  not build that runtime control itself.
- **FR-003**: When the current log file reaches a size threshold, the
  system MUST roll it over automatically and continue logging to a new
  file, without losing or interrupting in-progress logging.
- **FR-004**: The system MUST cap the total disk space used by log files
  at a fixed, predictable maximum — once old rolled-over data would push
  total usage past that maximum, the oldest data is pruned automatically.
- **FR-005**: A failure to write to the log file (missing directory, no
  permission, disk full, or anything else) MUST NOT prevent the
  application from starting, MUST NOT stop it from continuing to log to
  stdout, and MUST NOT fail the request being handled when the failure
  happens — consistent with feature 010's existing FR-007 guarantee,
  extended to this new destination.

### Key Entities

- **Log File**: The current, actively-written file containing log entries
  in the same form feature 010 already produces (per its JSON schema,
  unchanged by this feature).
- **Rolled-Over Log File**: A previous Log File, closed off after a
  rollover, retained until it falls outside the disk-usage cap (FR-004),
  at which point it's pruned automatically.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With file persistence enabled, 100% of log entries produced
  while the file is writable also appear in the log file, matching what
  appears on stdout.
- **SC-002**: Log entries written to the file remain readable after the
  application process has stopped, with no additional steps required to
  access them.
- **SC-003**: Total disk space used by log files never exceeds a fixed,
  predictable maximum, verified by producing enough log volume to trigger
  multiple rollovers and confirming usage stays capped throughout.
- **SC-004**: A broken log file destination (bad path, no permission)
  never prevents the application from starting or from serving requests,
  verified through testing.

## Assumptions

- File persistence defaults to **enabled**, since the core value of this
  feature — a real, openable file without extra setup — should work out
  of the box in local development, the primary environment without a
  log-collection platform behind it. It can be turned off via
  configuration for environments that don't want it (e.g. relying solely
  on stdout/CloudWatch capture).
- The exact size threshold and the exact number of rolled-over files
  kept before pruning are implementation/configuration details decided
  during planning, not scope decisions for this spec — the business
  requirement is only that both are fixed and predictable (FR-003,
  FR-004), per the explicit direction to take "the safest route" on
  rotation policy.
- This feature does not change feature 010's log content or JSON format
  in any way — it only adds a second destination (a file) for the same
  entries already being produced.
- The future admin panel that will let an operator choose local file vs.
  CloudWatch at runtime is a separate, later feature. This feature's only
  obligation toward it is to make file persistence an independently
  on/off capability now, so that future panel has something concrete to
  toggle rather than needing to rebuild this mechanism.
- This feature does not touch the AWS Lambda/Fargate production logging
  path (CloudWatch capture of stdout), which already works independently
  of anything this feature adds.
