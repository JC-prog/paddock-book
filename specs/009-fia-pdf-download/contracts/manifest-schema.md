# Contract: `manifest.json` Schema

One `manifest.json` file lives per `--output-dir` (i.e. per category). It is
a JSON object keyed by `source_url`; each value is a `ManifestEntry`
(see `data-model.md`).

```json
{
  "<source_url>": {
    "title": "string",
    "section": "string | null",
    "issue": "string | null",
    "published_date": "string (YYYY-MM-DD) | null",
    "local_filename": "string",
    "downloaded_at": "string (ISO 8601 UTC)"
  }
}
```

## Guarantees

- Every key is a unique, absolute source URL — the same URL never appears
  twice.
- An entry is only ever written after its PDF has been fully and
  successfully saved to disk; a partially-downloaded file never produces a
  manifest entry (so an interrupted run can't leave a manifest pointing at
  a corrupt/truncated PDF).
- The manifest is updated incrementally (one entry appended per successful
  download), not rewritten wholesale at the end of a run — an interrupted
  run's manifest still accurately reflects everything downloaded up to the
  interruption.
- `local_filename` is always a relative path within the same directory as
  `manifest.json` itself — never an absolute path or a path outside that
  directory.

## Consumers

This file has no consumer inside this feature beyond the tool's own
re-run/dedup check (FR-004). It is designed to be human-inspectable (SC-002)
and is a reasonable, but not yet built, input for a future automated bridge
into `modules/ingestion/` — deliberately not built now (see spec.md's
out-of-scope declaration).
