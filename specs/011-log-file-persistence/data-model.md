# Data Model: Log File Persistence

Not domain data — this describes configuration fields and the on-disk
file-naming scheme this feature introduces.

## Settings (additions to `core/config.py`)

| Field | Type | Default | Notes |
|---|---|---|---|
| `log_to_file` | `bool` | `True` | FR-002's toggle — on by default (spec.md Assumptions). |
| `log_file_path` | `str` | `"logs/app.log"` | Relative to the process's working directory (typically `backend/`). |
| `log_file_max_bytes` | `int` | `10485760` (10 MB) | Size threshold that triggers a rollover (FR-003). |
| `log_file_backup_count` | `int` | `5` | Number of rolled-over files retained before the oldest is pruned (FR-004). |

## Log File / Rolled-Over Log File (spec.md's Key Entities)

Produced by `logging.handlers.RotatingFileHandler`'s standard naming
convention — no custom code needed for this shape:

| File | Role |
|---|---|
| `app.log` | The current, actively-written Log File. |
| `app.log.1` | Most recently Rolled-Over Log File. |
| `app.log.2` … `app.log.5` | Older Rolled-Over Log Files, oldest last. |

When a rollover would produce more than `log_file_backup_count` files,
the oldest (`app.log.5` in the default configuration) is deleted
automatically — this is `RotatingFileHandler`'s built-in behavior,
directly satisfying FR-004.

Each file's content is one JSON object per line, in the exact shape
defined by feature 010's `contracts/log-schema.md` — unchanged by this
feature.
