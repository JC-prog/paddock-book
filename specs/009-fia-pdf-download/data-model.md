# Data Model: FIA Regulation PDF Downloader

## ListedDocument

Represents one document entry as found on a listing page, before it's been
downloaded. Produced by `listing.py`, consumed by `service.py`.

| Field | Type | Notes |
|---|---|---|
| `title` | `str` | Verbatim text of the `.title` div. Required — a listing entry with no title text is treated as a parse failure for that entry (skipped, reported), not a whole-page failure. |
| `source_url` | `str` | Absolute URL, resolved against `https://www.fia.com`. Required; this is the dedup identity (FR-004). |
| `section` | `str \| None` | Extracted from `title` (e.g. `"Section B [Sporting]"`). `None` if the title doesn't match the expected pattern. |
| `issue` | `str \| None` | Extracted from `title` via `Iss\.?\s*(\d+)` (case-insensitive). `None` if absent. |
| `published_date` | `date \| None` | Parsed from the `.published .date-display-single` span (`DD.MM.YY` → ISO date). `None` if the span is missing or unparseable. |

## ManifestEntry

Represents one successfully downloaded document, as persisted in
`manifest.json`. A superset of `ListedDocument` plus download-specific
fields. This is the record described in spec.md's **Downloaded Document**
key entity.

| Field | Type | Notes |
|---|---|---|
| `title` | `str` | Copied from `ListedDocument.title`. |
| `source_url` | `str` | Copied from `ListedDocument.source_url`. Manifest key — unique by construction (it's the dict key in `manifest.json`, not a duplicated field within each record). |
| `section` | `str \| None` | Copied from `ListedDocument.section`. |
| `issue` | `str \| None` | Copied from `ListedDocument.issue`. |
| `published_date` | `str \| None` | ISO `YYYY-MM-DD` string (JSON has no native date type). |
| `local_filename` | `str` | Filename the PDF was saved as, relative to the manifest's own directory. Derived from `source_url`'s path segment, sanitized. |
| `downloaded_at` | `str` | ISO 8601 UTC timestamp of when the download completed. |

**Manifest file shape** (`manifest.json`):

```json
{
  "https://www.fia.com/system/files/documents/fia_2026_....pdf": {
    "title": "FIA 2026 F1 Regulations - Section B [Sporting] - Iss 08 - 2026-08-05",
    "section": "Section B [Sporting]",
    "issue": "08",
    "published_date": "2026-08-05",
    "local_filename": "fia_2026_....pdf",
    "downloaded_at": "2026-08-08T14:32:01Z"
  }
}
```

Keyed by `source_url` for O(1) "already downloaded?" lookups (FR-004).

## DownloadFailure

Represents one document that was listed but could not be downloaded.
Collected during a run and surfaced in the run summary (FR-006, SC-004) —
never persisted to `manifest.json`, since it's not a successful download.

| Field | Type | Notes |
|---|---|---|
| `source_url` | `str` | The document that failed. |
| `title` | `str \| None` | Title if it was successfully parsed before the download itself failed. |
| `reason` | `str` | Human-readable failure reason (e.g. the underlying HTTP error). |

## DownloadRunResult

The summary produced at the end of one invocation of the tool — not
persisted, just returned/printed for the operator (the "Outstanding, low
impact" observability item noted during clarification: a natural default,
not something requiring its own manifest entry).

| Field | Type | Notes |
|---|---|---|
| `downloaded` | `list[ManifestEntry]` | Newly downloaded this run. |
| `skipped` | `list[str]` | Source URLs already present in the manifest before this run started. |
| `failed` | `list[DownloadFailure]` | Documents that could not be downloaded this run. |

## Relationships

- `ListedDocument` → (on successful download) → `ManifestEntry`, appended to
  `manifest.json` immediately, not batched.
- `ListedDocument` → (on failed download) → `DownloadFailure`, collected
  in-memory for the run's final report only.
- `manifest.json` is the single source of truth for "already downloaded";
  no separate index or database is maintained.
