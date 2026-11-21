## Review of feat-01 (rewrite-v7, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a Summary of 3 sentences plus one line on the current page behaviour and out-of-scope items, replacing the longer first summary.
- Moved all definitions into one Terms list, one line each, and defined every stack name a newcomer would not know (replica, keyset paging, job queue, attempt, multipart upload, lifecycle rule, signed link, export record, lease, heartbeat, checkpoint, etag, send_email).
- Kept all numbers and rules from the brief and the first version: 10,000-row threshold, 500-row and 5,000-row pages, 8 KB JSON limit, 60 s API kill, 50 s and 10,000-row abort, 512 MB worker, 30-minute attempt timeout, 3 attempts with 60 s and 300 s waits, 5 MB minimum part, 10,000-part limit, 8 MB buffer, about 115 parts, 20-minute budget, 5-minute lease, 45-minute stale rule, 5-second polling, 7-day expiry, 24-hour links, 409 and 503 responses.
- Rewrote the steps to say what starts each one, what data moves, where state is kept, and what happens on failure, with the same content as the first version.
- Replaced step-number codes that pointed elsewhere with named references, and kept the step numbers only for sequence.
- Merged repeated facts: the 24-hour lifecycle rule, the 2 MB and 12 MB memory notes, and the once-per-run lease explanation now each appear in one place.
- Added a table of what the user sees when things fail, separate from the per-step failure handling, which the brief requires.
- Moved the new pieces to build and the release checks into a Build and release section, kept apart from how the system runs.
- Turned the six decisions to confirm into Open questions at the end, each keeping its recommendation, and kept the known gaps in their steps.
- Added the single-line rationale for keyset paging (every page equally fast) and for the 10-minute time-budget margin, and the reason no cleanup job is built.
- Did not add any new mechanism, and no junior questions were supplied, so the rewrite is based only on the first version and the brief.

### Holes
- None.
