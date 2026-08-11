# Data Model: Download CLI Progress Bar

No persistent state or new entities — this feature adds no database
table, no file format, and no new dataclass. The only "shapes" it
introduces are two optional callback parameters on existing/new
functions in `download/service.py`.

## `on_progress` callback

| | |
|---|---|
| Signature | `Callable[[int], None]` |
| Called | After every document is processed by `download_category()` — downloaded, skipped, or failed alike |
| Argument | The running total of documents processed so far (not the total itself — the caller already knows that from `count_documents_in_category()`'s return value) |

## `on_failure` callback

| | |
|---|---|
| Signature | `Callable[[DownloadFailure], None]` |
| Called | Immediately when a document fails during `download_category()`'s download pass — before that same document's `on_progress` call (research.md) |
| Argument | The existing `DownloadFailure` dataclass (feature 009, unchanged: `source_url`, `title`, `reason`) |

## `on_page_counted` callback

| | |
|---|---|
| Signature | `Callable[[int], None]` |
| Called | After each listing page is counted by `count_documents_in_category()` |
| Argument | The 0-indexed page number just counted |

## Relationships

- All three callbacks are optional (`None` by default) on functions
  that already exist or are being added to `download/service.py` — none
  of them are a new type/entity a caller needs to construct; a caller
  just passes a plain function (or nothing at all, for unchanged
  behavior).
- `download/cli.py` is the only place in this codebase that ever
  supplies real implementations of these callbacks (wiring them to
  either a `tqdm` bar or plain print statements, per research.md's
  TTY/non-TTY split) — `service.py` itself never imports `tqdm` or
  inspects `sys.stdout`.
