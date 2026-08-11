# Feature Specification: Download CLI Progress Bar

**Feature Branch**: `015-download-progress-bar`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "Add a real-time progress bar to the FIA regulation PDF downloader CLI (modules/download/cli.py), which currently prints nothing at all while running and only shows a summary after the entire run finishes — for a full category (~240 documents, 8 pages) that's up to 40 minutes with zero feedback, making it impossible to tell whether the tool is progressing or hung. The progress bar must show a true bounded total (X of Y documents processed), not just a running count with an unknown total. Since the total document count isn't known until every listing page has been paginated through (feature 009's page-count-discovered-at-runtime design), this requires a separate, upfront counting pass that walks every listing page once purely to count documents, before the existing download pass begins — deliberately NOT restructured into a single collect-then-download pass, because that would remove the existing resilience guarantee (feature 009's SC-004) that a later page's fetch failure still leaves everything already downloaded from earlier pages intact; the upfront count only costs a small amount of extra time (one additional rate-limited walk of listing pages only, not PDF downloads) in exchange for preserving that guarantee. The progress bar must update as each document is processed — downloaded, skipped (already present), or failed — reaching the counted total when the run completes, and must work sensibly whether run in an interactive terminal or with output redirected to a file/log (no unreadable escape-code spam in a non-interactive context). Out of scope: adding progress reporting to the admin panel's background download job (feature 013's Celery-based job, which already has its own queued/running/succeeded status polling in the UI) — this feature is CLI-only; changing the downloader's actual download, skip-detection, or failure-handling logic — this feature only adds visibility into progress, not any change to what gets downloaded or how failures are handled; adding progress feedback to the PDF ingestion CLI or any other CLI in this project."

## Clarifications

### Session 2026-08-11

- Q: While the tool is walking listing pages just to count the total (before any downloading starts), should that counting step show any feedback of its own, or stay silent until it reports the total? → A: Show a lightweight running indicator during counting (e.g. "Counting documents... (page 4)"), then switch to the bounded X/Y bar once counting finishes.
- Q: When a document fails during the download pass, should the operator see that failure immediately as it happens, or only find out from the per-failure detail already printed in the final summary? → A: Show it immediately, printed inline without breaking the still-updating progress bar, in addition to the existing final summary.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Watch download progress in real time (Priority: P1)

An operator running the download CLI against a full regulation category sees a live-updating indicator of how many of the total documents have been processed so far, so they can tell the tool is genuinely working — not hung — and get a sense of how much longer a long run will take.

**Why this priority**: This is the entire point of the feature — closing the "up to 40 minutes with zero feedback" gap that currently makes the tool feel broken during a normal, expected-length run.

**Independent Test**: Can be fully tested by running the CLI against a category with documents across multiple listing pages and observing the progress indicator report a total before downloading starts, then advance as documents are processed, reaching that total when the run completes.

**Acceptance Scenarios**:

1. **Given** a category with documents across multiple listing pages, **When** the operator starts a download run, **Then** before any document is downloaded, the tool reports the total number of documents that will be processed.
2. **Given** the tool is still counting the total (before it's known), **When** the operator watches the output, **Then** they see a lightweight indicator of counting progress (e.g. which listing page is being counted) rather than silence.
3. **Given** a run is in progress, **When** a document is downloaded, skipped (already present from a previous run), or fails, **Then** the progress indicator advances to reflect it.
4. **Given** a document fails during the download pass, **When** the operator is watching the run live, **Then** they see that failure right away, without the progress display becoming garbled or unreadable.
5. **Given** a run completes, **When** the operator looks at the final state, **Then** the indicator shows the full total reached, consistent with the existing downloaded/skipped/failed summary already printed at the end.

---

### User Story 2 - Redirected output stays readable (Priority: P2)

An operator who redirects a download run's output to a log file — for a long, unattended run — gets a file that's still legible afterward, not corrupted by terminal control codes meant only for a live, interactive display.

**Why this priority**: A concrete, secondary failure mode if not handled: a run long enough to want live progress for is also long enough that operators plausibly want to background or redirect it, and this project has repeatedly found "behaves differently when piped vs. interactive" to be a real class of bug worth guarding against up front.

**Independent Test**: Can be fully tested by running the CLI with output redirected to a file, then reading that file back and confirming it's legible plain text, not raw escape-sequence noise.

**Acceptance Scenarios**:

1. **Given** the operator redirects a run's output to a file, **When** the run completes, **Then** the file contains readable text reflecting progress over time, not unreadable control sequences.

---

### Edge Cases

- What happens if determining the total itself fails (e.g., a listing page fetch fails during the counting pass)? The run reports a clear error and stops before downloading anything — consistent with how a listing-page fetch failure is already handled today.
- What happens if a listing page's fetch fails partway through the *download* pass, after counting already succeeded? Documents already downloaded before that point remain intact, exactly as today (feature 009's existing resilience guarantee) — this feature does not change that behavior.
- What happens when a document was already downloaded in a previous run (skipped this time)? It still advances progress, since it has still been *processed* — just not newly downloaded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST report the total number of documents to be processed before beginning to download any of them.
- **FR-001a**: While counting the total (before it's known), System MUST show a lightweight progress indicator of its own — e.g. which listing page is currently being counted — rather than staying silent until the total is available.
- **FR-002**: System MUST advance visible progress as each document is processed, whether downloaded, skipped, or failed.
- **FR-002a**: When a document fails during the download pass, System MUST surface that failure immediately, without disrupting or corrupting the still-updating progress display, in addition to the existing final summary's per-failure detail (FR-007).
- **FR-003**: The reported total MUST reflect every document found across the category's entire listing (all pages), not just the first page or an early partial count.
- **FR-004**: System MUST NOT change which documents are downloaded, skipped, or treated as failed — this feature only adds visibility into that existing, unchanged process.
- **FR-005**: System MUST preserve the existing guarantee that documents downloaded before a later failure remain intact — determining the total upfront MUST NOT weaken or remove this.
- **FR-006**: When output is redirected to a file rather than an interactive terminal, System MUST produce readable, non-corrupted text rather than raw control sequences intended only for a live display.
- **FR-007**: System MUST continue to print the existing final summary (counts downloaded/skipped/failed, per-failure detail) once a run completes.
- **FR-008**: If determining the total count itself fails, System MUST report a clear error and MUST NOT begin downloading — consistent with how a listing-page failure is already handled today, outside this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator running a full category download can see, at any point during the run, how many documents of the total have been processed so far, without waiting for the run to finish.
- **SC-002**: An operator can tell within the first few seconds of starting a run whether it is progressing, rather than needing to infer this from an arbitrary period of silence.
- **SC-003**: A run's redirected-to-file output remains fully readable text when reviewed afterward.
- **SC-004**: The existing resilience guarantee — documents downloaded before a later failure remain on disk — continues to hold exactly as it did before this feature.
- **SC-005**: The set of documents downloaded, skipped, or failed for a given run is identical to what it would have been without this feature — this is purely an added visibility layer, not a behavior change.
- **SC-006**: An operator watching a run live learns about a failed document at the moment it happens, not only after the entire run finishes.

## Assumptions

- This applies only to the standalone downloader CLI (`modules/download/cli.py`); the admin panel's background download job (feature 013) is unaffected — it already has its own status visibility (queued/running/succeeded) through the Jobs page, and is out of scope here.
- The upfront counting pass costs a small, acceptable amount of additional time (one extra rate-limited walk of listing pages only, not PDF downloads) in exchange for preserving the existing partial-progress-survives-a-failure guarantee — this tradeoff was deliberately chosen over a faster approach that would have given up that guarantee.
- No other CLI in this project (ingestion, admin promotion, background jobs, eval harness) is affected by this feature.
