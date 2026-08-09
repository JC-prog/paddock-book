# Research: Log File Persistence

## Rotation mechanism

**Decision**: `logging.handlers.RotatingFileHandler` (stdlib), configured
with `maxBytes` and `backupCount`.

**Rationale**: This is exactly what the "safest route" direction calls
for — a hard, predictable cap on total disk usage
(`maxBytes * (backupCount + 1)`) that holds regardless of traffic volume.
A time-based scheme (`TimedRotatingFileHandler`, e.g. daily) was
considered and rejected: a single unusually heavy day could still blow
past any reasonable size expectation before a time-based rollover would
trigger, which is a materially less safe guarantee for FR-004's "fixed,
predictable maximum."

**Alternatives considered**: `TimedRotatingFileHandler` — rejected per
above. A custom size-check-on-every-write wrapper — rejected as
reinventing what `RotatingFileHandler` already does correctly and simply.

## Concrete rotation numbers

**Decision**: `log_file_max_bytes = 10 * 1024 * 1024` (10 MB per file),
`log_file_backup_count = 5` — a hard cap of 60 MB total
(1 active file + 5 retained backups).

**Rationale**: Per spec.md's Assumptions, the exact numbers are an
implementation/configuration detail, not a scope decision — these are
reasonable, conservative defaults for a local-dev-first use case: large
enough that a normal debugging session doesn't rotate mid-investigation,
small enough that 60 MB is a trivial, unremarkable amount of disk to set
aside by default. Both are `Settings` fields, so they can be tuned via
`.env` without a code change if a real deployment needs something
different.

## Making it a togglable, non-hardcoded option

**Decision**: A new `Settings.log_to_file: bool` field, default `True`
(per spec.md's Assumptions — the feature's core value should work out of
the box in local dev). `configure_logging()` gains a `settings_factory`
parameter (default `Settings`, matching the DI pattern already used
throughout `modules/*/service.py`) so tests can inject a fake settings
object instead of needing real env vars.

**Rationale**: This directly satisfies FR-002 — file persistence is
already a config-driven on/off capability today, so the future admin
panel (out of scope here) has a concrete, existing switch to flip at
runtime later rather than needing this mechanism rebuilt from scratch.

## Graceful degradation when the file destination is broken (FR-005)

**Decision**: A small `_try_build_file_handler()` helper that creates the
log directory (`Path(path).parent.mkdir(parents=True, exist_ok=True)`)
and constructs the `RotatingFileHandler` inside a `try/except OSError`.
On failure, it returns `None`; `configure_logging()` then proceeds with
stdout-only logging and emits one `WARNING`-level line (via the stdout
handler, which is always set up first and unconditionally) naming the
problem, rather than either crashing or failing completely silently.

**Rationale**: Directly satisfies FR-005 and the "missing directory" /
"no permission" edge cases in spec.md. Proactively creating the parent
directory (rather than treating "doesn't exist yet" as an error) matches
the expected first-run local-dev experience — nobody should need to
`mkdir logs/` by hand before starting the app.

**Alternatives considered**: Letting the `RotatingFileHandler` constructor
raise straight into `configure_logging()`'s caller (`main.py`, at import
time) — rejected outright, since that would crash app startup entirely,
the opposite of what FR-005 requires.

**Real regression caught by the no-`.env` CI-parity check**: the
`settings_factory()` call itself — reading `Settings()` to even find out
whether `log_to_file` is on — was not originally wrapped in the same
protection. `configure_logging()` runs at import time in `main.py`, and a
real `Settings()` requires unrelated fields (`database_url`, `jwt_secret`)
with no defaults. In CI, which has no `.env` file at all, this meant
`from src.main import app` itself would have failed at import — breaking
every test file that imports it (`test_chat.py`,
`test_core_middleware.py`), not a narrow file-logging failure. Caught by
re-running `import src.main` with no `.env`/env vars (the same check this
project adopted after an earlier real CI failure), not by inspection.
Fixed by wrapping the `settings_factory()` call itself in the same
try/except-and-degrade pattern as the file handler, which is really the
same FR-005 guarantee applied one layer earlier: *any* failure to set up
file logging — including failing to read the settings that would decide
it — must degrade to stdout-only, not block startup.

## Reusing the existing JsonFormatter

**Decision**: The file handler uses the exact same `JsonFormatter`
instance shape as the stdout handler — same class, separately
instantiated per handler (formatters aren't shared mutable state here,
each handler gets its own instance, which is the standard `logging`
pattern).

**Rationale**: Directly satisfies SC-001 ("matching what appears on
stdout") and spec.md's explicit non-goal of changing feature 010's log
content/format. No new formatting code needed.

## Default file location

**Decision**: `Settings.log_file_path: str`, default `"logs/app.log"` —
resolved relative to the process's working directory, which in this
project's existing dev workflow is `backend/` (matching how `uvicorn
src.main:app` is already run per the project's quickstart docs). The
resulting default location is `backend/logs/app.log`, with rotated
backups alongside it as `app.log.1`, `app.log.2`, etc.
(`RotatingFileHandler`'s built-in naming convention).

**Rationale**: A relative default keeps this in step with the existing
`.env`-driven configuration story (all other `Settings` fields are
similarly environment-relative, not absolute-path assumptions baked in).

**Gitignore note**: the repository's `.gitignore` already has a bare
`*.log` pattern (from the Python template), which covers `app.log`
itself but not rotated backups like `app.log.1` (a different suffix, not
matched by `*.log`). This feature adds an explicit `backend/logs/`
directory ignore so the whole rotating set is covered regardless of
naming, rather than relying on the pre-existing partial pattern.
