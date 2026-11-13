## Review of dp-01 (junior-v5, author haiku, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added a guard to the MERGE: a matched row is updated only when the staged winner beats the stored row (later updated_at, ties by row hash). The brief requires the most recent version, and the plan had no such guard.
- Moved the success write into the same transaction as the MERGE and the hwm update, and removed the post-commit arrow (answers Q6).
- The hwm moves forward only. A late manual rerun of an older night must not move the watermark back (answers Q8).
- The 06:00 staleness check reads only etl_run_log; removed the etl_watermark edge (answers Q7).
- Stated explicitly that after the third failure nothing reruns automatically, that on-call reruns by hand with the same cutoff, and that the next night's window covers the missed night (answers Q8).
- Reconciliation now has explicit branches: it is skipped when Sunday's night has no success row, and it reloads when any row is missing or older in orders, alerting only when every difference is a newer row in orders. The diagram had no skip branch and left mixed differences undefined.
- Stated that reconciliation never changes the hwm and that a reload runs under its own run_id.
- Added the Terms section, the step-by-step text with what starts, keeps and does on failure for each step, and the failure table. Replaced the diagram's separate commit arrows for the success log with one transaction box.
- Clarified that a run's stage rows are cleared for its run_id before each attempt, so retries cannot double rows (answers the staging detail behind Q5 and retries).
- Per Q9: attempts are counted per run_id, and a manual rerun is a new run_id with the same 02:00 cutoff. Added step 8 and made the retry rule and the diagram count attempts per run_id.
- Per Q10: added run_kind (nightly or reload) to etl_run_log. The 06:00 check reads only nightly success rows. A reload's step 6 writes its success row but does not update the hwm, which resolves the conflict with 'reconciliation never changes the hwm'.
- Per Q11: the Sunday reconciliation is a separate weekly job, not triggered inside the nightly run. Its start time is left as an open question.
- Per Q12: stated that the reload takes a full extract of the creation day from the replica, ignoring the updated_at window, and that the MERGE rule replaces a stale stored row. Stated that the reload's staging rows are separate from the nightly run's rows.
- Per Q13: added a failure-table row for a scheduler that never starts a run, and an open question on who acts on the 06:00 alert.
- Per Q14: added an open question on whether dashboards filter on is_deleted.
- Added a failure-table row for a failed reload, and a sentence in the reconciliation section on what happens to it. Added a short paragraph on why the design is shaped this way.
- Added the controller to the terms, the steps, the diagram and the failure table, because the brief's retry rule needs something that waits 15 minutes and starts the next attempt (Q15).
- Rewrote step 7: attempts are counted from started rows, the controller writes a failed row when a process exits without one, and the next attempt starts only after the previous process has exited, so attempts never overlap (Q16).
- Added failure table rows for an attempt process that dies with no row and for a lost controller host.
- Added open questions for the hung-attempt time limit and for which host runs the controller.
- Rewrote the whole document once, for a newcomer, keeping the intent, the fixed requirements and all six open questions.
- Added terms in one line each for every table and name a reader asked about: `etl_run_log`, `orders_stage`, `recon_result`, run kind, attempt, controller, cutoff and lookback.
- Added short reasons where the junior asked why: the 2-hour overlap (late-visible rows would otherwise be skipped forever), the fixed 02:00 cutoff (retries must read the same window), the staging delete (retries cannot double rows), the MERGE guard (a newer stored row must not be overwritten), and the success row inside the transaction (it exists only if the night committed).
- Fixed a real gap: the controller now counts the attempts it has started for the run_id, not the started rows. A crash before the started row was written would otherwise go uncounted and allow extra attempts. The started row is still written for history. Updated the diagram and step 7 to match.
- Fixed the MERGE rule so a matched row updates only when the staged winner beats the stored row (later updated_at, ties by larger row hash). This was the guard the junior asked about.
- Cut the duplicate reconciliation prose that repeated the diagram, and the repeated 'reads no other table' and 'reload is ignored' statements, leaving one statement each.
- Merged the started-row and failed-row rules into steps 1 and 7, and the attempts-never-overlap rule into step 7 and the diagram notes.
- Changed 'last 30 full days' to the brief's 'last 30 days' in the diagram and text, because 'full' was not in the brief.
- Removed the '#data-alerts' label from the diagram and used 'the data-alerts channel', because '#' can break Mermaid labels. The prose still names #data-alerts.
- Removed the codes-style references and kept step numbers only. Added a short 'Build and rollout' section that separates setup settings from how the system runs.
- Added to the failure table a row for an attempt process that never exits, which previously appeared only in the open questions.

### Holes
- Q3: How does the first run know there is no watermark, and what is the 'configured backfill start' and where is it configured? (author: The first run is detected by the absence of an hwm row. The brief names no backfill start date and no place where it is configured, so both are unknown. Listed under open questions.)
- Q13: If the scheduler never starts the run at all, nothing is written to etl_run_log. Is the 06:00 staleness alert the only thing that catches that, and who acts on it? (author: Yes, in this plan the 06:00 staleness check is the only thing that catches a run the scheduler never starts, because no run row exists. The brief names no owner for the staleness alert, so who acts on it is unknown. Added as an open question.)
- Q14: Deleted orders stay in orders as flagged rows with is_deleted set. Do dashboards filter on is_deleted, or is that left to the analysts? (author: The plan keeps deleted orders as rows with is_deleted set, and it does not say whether dashboards filter on it. The brief does not decide this. Added as an open question.)
