# Quickstart: Download CLI Progress Bar

## Prerequisites

- `backend/.venv` set up with this feature's new dependency installed
  (`tqdm` — see `backend/requirements.txt`)
- Internet access to `www.fia.com`/`api.fia.com` (same as feature 009)
- **Time**: reaching the full counted total for category 110 still
  takes the same ~40 minutes feature 009's own quickstart already
  documented (this feature doesn't change download speed, only adds
  visibility) — the steps below validate the new behavior without
  needing a full run to finish. The new counting pass itself adds
  roughly another 80 seconds up front (research.md).

## Steps

1. **Counting-phase feedback (FR-001a)**

   ```
   cd backend
   python -m src.modules.download.cli --category 110
   ```

   **Expected**: within the first few seconds, visible output showing
   counting progress (an indeterminate bar or page-by-page text,
   depending on your terminal) — never silence during the ~80-second
   counting pass. Once counting finishes, the tool reports a total
   count before any PDF download begins (FR-001).

2. **Bounded progress during download (FR-002, FR-003)**

   Let the run continue for a minute or two after counting finishes.

   **Expected**: a bar (or line, depending on terminal) showing
   `X/Y` advancing as documents are downloaded, `Y` matching the total
   reported in step 1. Interrupt (`Ctrl+C`) once you've observed it
   advance — no need to wait for the full run.

3. **Resilience is unchanged (FR-005, SC-004)**

   ```
   ls data/regulations/110/*.pdf | wc -l
   cat data/regulations/110/manifest.json | python3 -c "import json,sys; print(len(json.load(sys.stdin)))"
   ```

   **Expected**: the PDF count and manifest entry count match, and
   both reflect exactly what was downloaded before the interrupt in
   step 2 — identical to how an interrupted run already behaved before
   this feature (feature 009's own quickstart validates this same
   property).

4. **Re-running shows skipped documents still advancing progress (Edge Cases)**

   ```
   python -m src.modules.download.cli --category 110
   ```

   **Expected**: counting reports the same total `Y` as before;
   progress advances through the documents from step 2/3 quickly (they
   count as "skipped," per the existing manifest check), then continues
   into genuinely new downloads.  Interrupt again once satisfied.

5. **Redirected output stays readable (FR-006, SC-003, US2)**

   ```
   timeout 90 python -m src.modules.download.cli --category 110 > /tmp/download-run.log 2>&1
   cat -v /tmp/download-run.log | head -30
   ```

   (On macOS without GNU `timeout`, just run it plainly and `Ctrl+C`
   after ~90 seconds instead.)

   **Expected**: the file contains plain, readable lines — counting
   progress, then periodic `Progress: X/Y (N%)` lines — with no `^M`
   (carriage return) or other control-sequence artifacts from `cat -v`.
   Contrast this directly against `research.md`'s documented finding
   that naive `tqdm` usage produces exactly that kind of corruption.

6. **A failure is visible immediately, not just at the end (FR-002a, SC-006)**

   Hard to force deterministically against the real site. Validated
   primarily via the unit tests covering `on_failure` (`tasks.md`) —
   consistent with how feature 009's own hard-to-force failure paths
   were validated. If you want to see it live: interrupt your network
   connection briefly during a run (per feature 009's own quickstart
   technique) and watch for the failure line appearing inline, not only
   in the final summary.

## Cleanup

Nothing new to clean up beyond feature 009's own guidance — the
`data/regulations/110/` archive built up across these steps is real,
reusable data (same as before this feature).
