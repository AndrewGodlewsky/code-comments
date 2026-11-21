## Review of dp-01 (rewrite-v5, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Summary: rewritten as one plain paragraph that says what the job does from start to finish and why the overlap exists. Removed codes and jargon that needed lookup.
- Terms: added a terms section with one-line definitions for replica, warehouse, updated_at, deleted_at, HWM, window, staging table, MERGE, lock, run date, attempt, creation day and checksum. Merged the 'Where things live' table into it as the place where state is listed.
- Schedule (fixed contradiction): the original said attempts run at fixed times 02:00, 02:15 and 02:30 and also said each retry starts 15 minutes after a failed attempt. With a 50-minute timeout, fixed times would overlap and the lock would make later attempts fail at once. Kept the 'after the previous attempt ends' rule, which matches the brief's 'retry 15 minutes apart'.
- Timing claim (fixed): the original said three attempts end 'before 05:00'. Worked out, the worst case ends at exactly 05:00. Changed the wording to 'by 05:00', with the times written out. The 06:00 check still has an hour of margin. No timeout value was changed.
- Flowchart: added the edge from a held lock to the failure path, which the original text described but the diagram lacked. Changed the retry box to release the lock only when this attempt holds it, so a held lock is never released by another run. Added an alert branch after the reconciliation re-check, which the text described but the diagram lacked. Replaced 'order-creation day' with 'creation day' in the diagram.
- First-run backfill (added): the original said the first H is set by a one-time backfill but did not say how. The plan now sets H to 1970-01-01 UTC, so the first normal run loads the whole table. This is a design choice I made, recorded here, and it is listed as an open question about the 50-minute timeout.
- Steps: rewrote the Extract, Stage, Validate, Merge and commit, Failure and Reconciliation sections as numbered steps, each saying what starts it, what it does, what keeps its data and what happens when it fails. Merged the duplicated lock and idempotency rules into the start and lock steps, and the duplicated failure rules into one failure step and one table.
- Merge rule: kept the same logic. Explained in words that a staged row replaces the live row only when newer, and that new orders are inserted with loaded_at set. Dropped the raw SQL, since the plan does not need the exact syntax.
- Failure table (added): one table listing each failure, where it happens, and what happens, replacing failure rules spread across several sections.
- Build and roll out (added): separated build and rollout steps from how the system runs, as the skill requires. Moved the MERGE and transaction support check and the created_at check here, from the old assumptions list.
- Open questions: removed the open boundary that said missed nights are covered only 'provided the gap stays within the 2-hour margin logic'. That was wrong. The HWM does not move when a night fails, so the next successful window reaches back to it and covers any gap, at the cost of a bigger extract. Rewrote the item to say so.
- Open questions: added the question of whether Sunday reconciliation runs when that Sunday's load failed, because the plan only starts it after a commit. Added the first-run timeout question. Kept the created_at, 30-day, equal-updated_at and UTC questions.
- Cut: removed the detailed 'why the lookback is enough' proof from the main text. The reasoning is now one sentence in the summary, and the main flow does not depend on it. Removed the separate stand-alone reconciliation checksum example, folding it into the term 'checksum'. Removed repeated statements that the staging table is per attempt. Stated once in the steps.

### Holes
- None.
