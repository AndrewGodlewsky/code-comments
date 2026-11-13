## Review of dp-01 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Rewrote the diagram so every step has edges: what starts each step, which tables and sources it reads or writes, and where failures and retries go. The original had nodes with no connections for the watermark, run log, deadline check, alerts, or reconciliation.
- Added a Terms section defining replica, warehouse, high-water mark, lookback, staging, and soft delete, so a reader new to the project can follow the document.
- Added a Where state lives section listing the four warehouse tables that hold pipeline state and output.
- Spelled out the merge logic: dedupe staging by latest updated_at, MERGE on order_id with a greater-updated_at rule, is_deleted from deleted_at, and why re-runs are harmless.
- Spelled out staging: staging is emptied at the start of each attempt, and the replica is read-only.
- Spelled out the high-water mark: how the window is derived, how the new cutoff is chosen (captured before the query), and that the HWM advances in the same transaction as the merge, so a failed run leaves it unchanged.
- Made the retry rule explicit: three attempts in total, with attempts 2 and 3 starting 15 minutes after the previous failure, and a page only after attempt 3 fails. The original said 'retries, then pages', which was ambiguous.
- Explained why dashboards never see a half-loaded night: the whole merge, HWM update, and run log commit as one transaction.
- Added a section on the 06:00 deadline check, stating what it reads, what it posts, and that it does not affect the job.
- Expanded the Sunday reconciliation: how counts and checksums are computed on both sides, what triggers a reload, and that reconciliation does not move the HWM.
- Added an Assumptions to confirm section for points the brief leaves open: the first-run HWM, Sunday reconciliation when that night did not load, and failed reloads.
- Defined the terms 'night', 'attempt', 'window start', 'new cutoff' and 'order-creation day' so a reader new to the project can follow the steps.
- Added a short explanation of why the 2-hour lookback exists (90-minute open bulk-import transactions, and updated_at stamped at write time), placed before the steps.
- Stated why the new cutoff is recorded before the extract query runs, and that it becomes the HWM only on commit.
- Clarified that staging is emptied at the start of every attempt and that the extract copies rows unchanged.
- Made it explicit that steps 4a to 4e are one transaction with all-or-nothing commit, and moved that rule to the top of step 4.
- Explained the merge rule in plain terms: an older copy never overwrites a newer one, so re-running a window changes nothing; deletes follow the same rule because they are writes.
- Explained the checksum in plain words (sum of a per-row hash, so order does not matter) and why timestamps are normalised to UTC.
- Reworded the 06:00 check and the reconciliation intro so the purpose of each is clear, and noted that the nightly job cannot see the late rows.
- Kept the Mermaid diagram's nodes, labels and arrows unchanged, and kept the document's section structure and format.
- Rewrote sentences to be shorter and to state one idea each, and used plainer words (for example, "copy" for "extract" where it helps, and "changes" for "writes").
- Defined terms the reader may not know: bulk import, soft delete, merge (upsert), and the lookback's purpose, which is now explained in plain language with its cost (duplicate extraction).
- Added a plain-language explanation of the lookback, so the reason for the 2-hour window is clear without knowing the app.
- Step 1 now says what the start row in etl_runs contains.
- Step 2 now explains why the cutoff is recorded before the extract query runs, in terms of the next night's window.
- Step 3 now says staging is emptied before the copy, and that the replica is only read.
- Step 4c now states that the rule applies to rows whose deleted_at is set, and that deleted rows are never removed.
- Failure section now states that an attempt's etl_runs row is updated to "failed" in a separate write outside the merge transaction. Without this, "a failed attempt commits nothing" appeared to conflict with logging the start row.
- Moved the Sunday skip rule (if Sunday's load did not commit) into the reconciliation section itself, so it reads with the rule. It stays listed under assumptions too.
- Reconciliation steps renamed to Compare, Reload, and HWM, and the checksum is explained as a sum of per-row hashes.
- The Mermaid diagram is unchanged, apart from indentation, and the legend above it is unchanged.

### Holes
- None.
