## Review of dp-01 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Rewrote the opening paragraph in plain words and defined the high-water mark on first use.
- Simplified the Mermaid flowchart: shorter node labels, all labels quoted, fewer redundant nodes, and one clear failure path.
- Fixed the retry arrow so a retry re-enters at the lease step, matching the notes.
- Added the 'skipped' value to the recon_results action list, since the notes already record skipped reconciliations.
- Stated that a failed attempt rolls back the warehouse transaction.
- Explained terms such as lookback, keyset paging, snapshot, MERGE, lease and checksum in the notes.
- Added the requirement that all keyset pages read from one replica snapshot.
- Clarified the lookback arithmetic in steps.
- Added open items: lease expiry versus run length and a lease check inside the MERGE transaction; the 30-day reconciliation limit; reloads cannot move rows backwards; and reload commits being visible one day at a time.
- Added a short "Terms used below" list (replica, warehouse, high-water mark, lease, snapshot, staging, MERGE, transaction) so a reader new to the project and stack can follow the rest.
- Rewrote the opening paragraph in plain terms: what the job reads, where it writes, what the high-water mark means, and when dashboards see data.
- Explained keyset paging and why all pages come from one snapshot, instead of only naming them.
- Replaced "tonight" in the Sunday reconciliation notes with "that night's load" and defined it as the run that started at 02:00 UTC that day.
- Clarified the retry timing: the next attempt starts 15 minutes after the failed attempt ends, with at most three attempts.
- Expanded the lookback argument into explicit steps (commit after S, updated_at up to 90 minutes earlier, next window starts at H_new minus 2 hours) so the reason the 2-hour window covers bulk imports is easy to follow.
- Defined a conditional UPDATE and the lease behavior in plain words, and noted that a deleted order arrives as an update.
- Explained that equal checksums on both sides follow from the same ordering and conversion rules.
- Kept the Mermaid flowchart unchanged, and kept the notes structure, merge rules, state tables, and open items with their original meaning.
- Added a plain-language definitions list for attempt/run, lookback, keyset paging, and the other terms, so a reader new to the project and the stack can follow the rest.
- Rewrote the opening paragraph to say what the job does and why, in plain terms (what a replica is, what the high-water mark means, why dashboards see only committed data).
- Reworded diagram labels to be plainer (for example 'Is the lease free?' and 'Log as skipped and exit') and made the start and window steps explicit ('first ever run: no lower bound'). Node IDs, edges, and the step structure are unchanged.
- Clarified the 2-hour lookback explanation as a step-by-step argument: the row becomes visible up to 90 minutes after its updated_at, the window starts 2 hours before the snapshot, and the 30-minute margin covers clock skew.
- Replaced jargon such as 'MERGE-guarded' and 'write-sequence tie-break' with short definitions in place, and said 'attempt' consistently where the old text mixed 'attempt', 'run', and 'job'.
- Explained the lease as a conditional UPDATE in plain words and described keyset paging and snapshots where they first appear.
- Tightened the assumptions list wording without changing any assumption, and kept every design decision and open item from the original.

### Holes
- None.
