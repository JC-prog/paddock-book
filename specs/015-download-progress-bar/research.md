# Research: Download CLI Progress Bar

## `tqdm`'s default behavior fails FR-006 — verified directly, not assumed

**Decision**: The CLI checks `sys.stdout.isatty()` itself and renders
progress two different ways — a real `tqdm` bar when connected to an
interactive terminal, and plain, throttled, newline-terminated status
lines (no `tqdm` involvement at all) when it isn't. `tqdm`'s own
`disable=None` auto-detect flag is deliberately **not** used as the
whole solution.

**Rationale**: Tested directly against the installed `tqdm` (4.70.0),
not assumed:

1. Plain `tqdm(range(5), desc="Testing")` with output redirected to a
   file writes raw `\r` (carriage return) bytes into the file
   unconditionally — confirmed by inspecting the file's raw bytes
   (`b'\rTesting: 0%|...'`, repeated per update). Read back later,
   that's exactly the "unreadable control-sequence spam" FR-006 exists
   to prevent. `tqdm`'s default `disable` value is `False`, not an
   auto-detecting `None` — non-TTY awareness is opt-in, not automatic.
2. Passing `disable=None` (tqdm's documented "disable on non-TTY" flag)
   does fix the corruption — but verified it does so by suppressing
   *all* output in a non-TTY context, not by degrading to readable
   plain-text lines. That satisfies "non-corrupted" but not this
   feature's own acceptance scenario text: "the file contains readable
   text reflecting progress over time" (US2 Scenario 1) — silence
   isn't "reflecting progress over time."

Neither of `tqdm`'s two built-in behaviors (always-redraw, or
auto-silent) matches what spec.md actually asks for. The CLI therefore
owns the TTY/non-TTY branch itself: `tqdm` only for the genuine
interactive case (its normal, extremely well-established behavior,
which does not need further verification here); a small, separate
plain-line renderer for the non-interactive case.

**Alternatives considered**: Relying solely on `disable=None` — rejected
per the above, it under-delivers on the "still shows progress" half of
FR-006/US2. Always using `tqdm` unconditionally — rejected, corrupts
redirected output (the core bug this feature must not introduce).

## Non-interactive stdout needs explicit line-buffering — found via a real, live test, not anticipated at plan time

**Decision**: `_run_with_plain_progress()` calls
`sys.stdout.reconfigure(line_buffering=True)` before printing anything.

**Rationale**: Discovered during implementation by actually running the
CLI with output redirected to a file and killing it mid-run (simulating
an operator checking a log while a long run is still in progress, or
the process dying unexpectedly): the log file was completely empty,
even though multiple `print()` calls had already executed. Verified
directly, isolated from this feature's own code: Python fully buffers
(not line-buffers) `stdout` by default whenever it isn't a TTY, so
`print()` output only reaches the file once the internal buffer fills
or the process exits *normally* — a process killed by `SIGTERM` doesn't
get that chance. Without this fix, a redirected run's output is only
reliably "readable, reflecting progress over time" (FR-006/US2) *after*
the whole run finishes — which fails the actual point of redirecting a
long-running process's output to check on it while it's still going.

**Alternatives considered**: Passing `flush=True` to every individual
`print()` call — rejected as more repetitive and easier to forget on a
newly-added print statement later, versus one `reconfigure()` call that
covers all output from that point on.

## The counting pass and the download pass stay fully separate functions

**Decision**: `count_documents_in_category()` is a new, standalone
function in `download/service.py` — it repeats
`download_category()`'s own page-walking loop (same
`CATEGORY_URL_TEMPLATE`, same `listing.parse_listing_page()`/
`has_next_page()` calls, same rate limiter pattern) but only tallies
`len(documents)` per page; it never calls `fetch_pdf` and never touches
the manifest. `download_category()` itself is not restructured — it
keeps its existing single-pass, page-by-page, download-as-you-go
architecture exactly as before, just with two new optional callback
parameters.

**Rationale**: This is the load-bearing decision from pre-specify
planning (spec.md Assumptions): a merged collect-all-pages-then-download
architecture would mean a listing-page failure during collection loses
*all* progress, not just what's left; keeping the passes separate
preserves `download_category()`'s existing, tested resilience
guarantee (a later page's failure still leaves earlier pages' downloads
on disk) untouched. The cost — one extra rate-limited walk of listing
pages only — is small relative to the ~40-minute full run PDF downloads
already dominate (plan.md's Performance Goals).

**Alternatives considered**: Restructuring into one collect-then-download
pass — rejected for the resilience regression above, which is exactly
what this decision was made specifically to avoid (spec.md's own input
text names this explicitly).

## `download_category()` reports progress via two optional callbacks, not a return-value change

**Decision**: `download_category()` gains `on_progress: Callable[[int], None] | None = None`
(called after every document is processed — downloaded, skipped, or
failed — with the running total processed so far) and
`on_failure: Callable[[DownloadFailure], None] | None = None` (called
immediately when a document fails, before `on_progress` for that same
document). Both default to `None`; existing callers/tests that don't
pass them see no behavior change at all.

**Rationale**: This is the same DI-callback pattern this function
already uses for `fetch_page`/`fetch_pdf`/`rate_limiter` — consistent
with the codebase's established style, and it keeps `service.py` fully
ignorant of *how* progress gets rendered (no `tqdm` import, no
TTY-detection logic) — that stays entirely in `cli.py`, matching the
plan's structure decision (service.py = behavior, cli.py = rendering).
Splitting `on_failure` out from `on_progress` (rather than having the
CLI inspect the running `failed` list itself) is what makes FR-002a's
"show it immediately" requirement possible — `on_progress` alone only
reports a count, not *what* just happened.

**Alternatives considered**: A single combined callback receiving the
whole in-progress `DownloadRunResult` each time — rejected as a needless
larger surface (would require constructing/copying that object on every
single document, when only a count and an optional failure are ever
actually needed).

## Counting-phase feedback (FR-001a) uses the same TTY/non-TTY split

**Decision**: `count_documents_in_category()` takes an optional
`on_page_counted: Callable[[int], None] | None = None`, called after
each page is counted with the page number. The CLI renders this the
same way as download progress: an indeterminate `tqdm` bar (no known
total yet) when interactive, a plain "Counting documents... (page N)"
line when not.

**Rationale**: Consistent rendering strategy for both phases, and reuses
research.md's TTY-detection finding rather than introducing a second,
different mechanism for what is conceptually the same problem (show
progress, whether or not a total is known yet).
