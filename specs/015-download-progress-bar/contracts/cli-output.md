# Contract: Download CLI Output

Invocation is unchanged (feature 009):

```
python -m src.modules.download.cli --category <id> [--output-dir <path>]
```

This contract covers only what changes: the CLI's *observable output*
during a run. Exit codes and the final summary are unchanged from
feature 009.

## Interactive terminal (stdout is a real TTY)

1. **Counting phase**: an indeterminate `tqdm` bar (no total shown yet,
   since it isn't known) advancing per listing page counted, labeled
   distinctly from the download phase (e.g. "Counting documents...").
2. Once counting finishes, the bar switches to a bounded `X/Y` bar for
   the download phase, `Y` being the just-counted total.
3. **On any document failure**: printed inline via `tqdm`'s
   write-without-corrupting-the-bar mechanism, immediately — the bar
   keeps advancing normally afterward (FR-002a).
4. **On completion**: the bar reaches `Y/Y`, then the existing final
   summary (feature 009: counts + per-failure detail) prints as before.

## Redirected / non-interactive output (stdout is not a TTY)

No `tqdm` involvement at all (research.md) — plain, newline-terminated
lines only:

1. **Counting phase**: one line per listing page counted, e.g.
   `Counting documents... (page 4)`.
2. Once the total is known: one line reporting it, e.g.
   `Found 240 documents. Starting download.`
3. **During download**: throttled plain-text progress lines — one
   whenever cumulative progress crosses each 10% boundary of the total
   (e.g. `Progress: 24/240 (10%)`, `Progress: 48/240 (20%)`, ...) —
   frequent enough to show real movement over a long run without
   spamming a line per document.
4. **On any document failure**: printed immediately as its own line
   (e.g. `FAILED: <source_url> (<title>): <reason>`), regardless of the
   10%-boundary throttling above — failures are never batched or
   delayed (FR-002a applies identically in both rendering modes).
5. **On completion**: the existing final summary prints as before
   (unchanged from feature 009).

## Error handling (both modes)

If the counting pass itself fails (e.g. a listing-page fetch error),
the run prints a clear error to stderr and exits non-zero *before* any
download attempt or manifest write — identical in spirit to how a
listing-page failure during the download pass has always been handled
(uncaught, feature 009), just now happening slightly earlier in a run
(during counting instead of downloading) when it's the counting pass
that hits it.

## Non-goals

- No change to what gets downloaded, skipped, or recorded in the
  manifest (FR-004) — this contract covers *output* only.
- No change to the admin panel's background download job (feature
  013) — its own status polling in the Jobs page is untouched.
- No new CLI flags — an operator cannot opt out of progress reporting;
  it's always on, rendered appropriately for the output destination.
