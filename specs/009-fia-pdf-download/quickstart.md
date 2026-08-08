# Quickstart: FIA Regulation PDF Downloader

Validates the tool end-to-end against the real FIA site. This is a manual
validation guide, not an automated test — see `research.md`'s note on why no
automated test hits the live site.

## Prerequisites

- Backend virtualenv set up per the repo's normal `backend/` setup
  (`pip install -r requirements.txt`, including the new `beautifulsoup4`
  dependency added by this feature).
- Internet access to `www.fia.com` / `api.fia.com`.
- **Time**: a full first-time run against category 110 (~240 documents,
  8 pages) takes roughly 40 minutes, dominated entirely by the mandatory
  10-second crawl-delay between requests (FR-005) — this is expected, not a
  performance bug. The steps below validate correctness without needing to
  wait for a full run to finish.

## Steps

1. **First run, interrupted partway through**

   ```
   cd backend
   python -m src.modules.download.cli --category 110
   ```

   Let it run through the first listing page (~30 documents, ~5 minutes),
   then interrupt it (Ctrl+C) once you see several PDFs saved under
   `data/regulations/110/`.

   **Expected**: `data/regulations/110/manifest.json` exists and contains
   one entry per PDF actually saved to disk before the interrupt — matching
   SC-004 ("previously-downloaded documents remain intact" after a
   disruption). No entry references a file that doesn't exist on disk.

2. **Inspect a manifest entry**

   Open `data/regulations/110/manifest.json` and confirm one entry has all
   of: `title`, `section`, `issue`, `published_date`, `local_filename`,
   `downloaded_at` — matching `contracts/manifest-schema.md`. At least one
   entry should have a non-null `issue` and `published_date` (SC-002).

3. **Re-run and confirm skip behavior**

   Run the same command again:

   ```
   python -m src.modules.download.cli --category 110
   ```

   **Expected**: the run summary reports the previously-downloaded
   documents as `skipped` (not re-downloaded — no 10-second wait incurred
   for them), and the run resumes fetching new documents starting from
   where it left off (SC-003). Confirm via the printed summary and by
   checking that the already-downloaded PDFs' `downloaded_at` timestamps in
   `manifest.json` are unchanged from step 1.

4. **(Optional, ~40 min) Full run to completion**

   Let a run go all the way through every page. **Expected**: the final
   summary's `downloaded` + `skipped` count matches the total number of
   documents visible when manually browsing
   `https://www.fia.com/regulation/category/110` through all its pages
   (SC-001), and `failed` is empty (or, if the site had a transient issue,
   each failure is clearly reported with its URL and reason per FR-006).

5. **Broken-link / failure handling (manual spot check)**

   Temporarily point `--output-dir` at a fresh empty directory and run
   against a category, but interrupt your network connection briefly
   partway through (e.g. disable Wi-Fi for a few seconds) to force a
   request failure.

   **Expected**: the run continues past the failed document rather than
   crashing, and the failure appears in the final summary with its source
   URL and a reason (FR-006). Previously-downloaded documents in that run
   remain on disk and in the manifest.

## Cleanup

`data/regulations/` is gitignored — delete it locally when done
experimenting; nothing here needs to be committed.
