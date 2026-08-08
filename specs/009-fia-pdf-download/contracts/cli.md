# Contract: Download CLI

## Invocation

```
python -m src.modules.download.cli --category <category-id> [--output-dir <path>]
```

| Argument | Required | Default | Notes |
|---|---|---|---|
| `--category` | Yes | — | The FIA regulation category ID, e.g. `110` for `https://api.fia.com/regulation/category/110`. |
| `--output-dir` | No | `data/regulations/<category-id>` (relative to repo root) | Where PDFs and `manifest.json` for this category are stored. |

## Behavior

1. Resolves the category listing URL from `--category`.
2. Walks every listing page (see `research.md` — Pagination) until no
   further page is found.
3. For every listed document not already present in `<output-dir>/manifest.json`:
   - Waits at least 10 seconds since the tool's previous request to the
     source site (FR-005).
   - Downloads the PDF.
   - On success: saves the file under `<output-dir>`, appends a
     `ManifestEntry` to `manifest.json` immediately, and records it as
     `downloaded` in the run summary.
   - On failure (network error, non-200 response, etc.): records a
     `DownloadFailure` in the run summary and continues to the next
     document (FR-006) — does not abort the run.
4. Documents already present in the manifest are recorded as `skipped` and
   are not re-fetched (no network request, no crawl-delay wait incurred).
5. Prints a run summary to stdout: counts of downloaded / skipped / failed,
   and for each failure, its source URL, title (if known), and reason.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Run completed — including the case where some individual documents failed (failures are reported, not fatal; see FR-006). |
| `1` | The run could not proceed at all — e.g. the category's first listing page itself could not be fetched, or `--category` was not provided. |

## Non-goals (explicitly out of scope — see spec.md)

- Does not parse, chunk, embed, or otherwise feed downloaded PDFs into
  `modules/ingestion/` — that remains a separate, manual step.
- Does not assign a department/business category to any document.
- Does not schedule or re-run itself; each invocation is a single manual run.
