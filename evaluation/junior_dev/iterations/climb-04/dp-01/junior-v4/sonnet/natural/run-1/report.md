## Review of dp-01 (junior-v4, author sonnet, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Run log lock is now one running row across all kinds, so nightly and recon cannot overlap (fixes a real flaw)
- Lock busy now logs a failed attempt that follows the normal retry rule
- Added stale running row cleanup at the start of each attempt, to recover from crashes
- Defined the runner as the single component that waits, retries, pages and starts recon; updated the trigger table and flowchart labels
- Explained the 90 minute bulk-import lag in the Extract section
- Clarified that validation compares raw counts on one snapshot, and corrected the duplicates wording in the flowchart and merge logic
- Added recon log identity: kind=recon, same run_date, own attempt counter starting at 1
- Watchdog now checks for a committed nightly row, so a recon row cannot satisfy it
- Added Open questions for the missing recovery signal after a late commit and for a dead runner
- Flowchart step 6 now starts with a check that the attempt's own run_log row is still running, else rollback, so a timed-out or stale attempt cannot commit late (Q9).
- Failure and retry: added how the 60 minute timeout is enforced (runner kills the attempt process) and the late-commit guard (Q9).
- Flowchart R5 and the recon section: recon gets the same own-row-still-running check and an explicit 60 minute timeout, also shown in the RECON subgraph title (Q10).
- Where state lives: stale cleanup now says 60 minutes for every running row, nightly or recon (Q10).
- Sunday reconciliation Compare: said the runner does the comparison, the replica side is one snapshot, the warehouse side is read separately, and false positives come from that gap (Q11).
- Failure and retry and the trigger table: page on-call applies to a third recon failure too, with a message naming recon; paging tool declared outside the design (Q12).
- ops.etl_state: seed rule stated (earlier than oldest updated_at, first run uses the normal path); added an Open question about history that may not fit in 60 minutes (Q13).
- Staging rows now carry run_id; each attempt deletes rows of finished runs instead of truncating, and validates and merges only its own rows (flowchart L4, L5, L6, STG node, Where state lives, Merge SQL WHERE clause). Fixes a lingering process corrupting a later attempt's staging.
- Added a Failure and retry bullet, No overlap between attempts, explaining why the stale cleanup and the 60-minute kill do not race and what protects core and staging if a process lingers.
- Recon reload now states a single REPEATABLE READ snapshot and a staged-count check before the merge (flowchart R4 and Reload bullet).
- Added a Purpose bullet to Sunday reconciliation: what it catches and what it cannot fix.
- Expanded False positives to say recent creation days can mismatch because the warehouse stops at the nightly hi, and that this is expected and harmless.
- Added a note in Staleness that the watchdog ignores recon, so a failed recon only pages on-call and dashboards are unaffected.
- Reordered into the newcomer layout: summary (with a note that this is a new pipeline), terms, diagram, run steps, failure table, setup and assumptions, open questions.
- Added a short Terms list (runner, attempt, HWM, lookback, staging, soft delete, recon), each in one line.
- Rewrote the nightly flow and the Sunday recon as numbered steps that each give what starts them, what they do, which store holds the data, and what happens on failure.
- Merged the scattered failure bullets (Failure, Timeout, A timed-out attempt cannot commit late, No overlap between attempts, Retry, Retry window, Third failure, Runner dies) into one failure table.
- Merged the High-water mark, Extract and Merge sections into the nightly steps and the merge section, so the HWM update, the monotonic GREATEST and the single-transaction guarantee are said once.
- Replaced the state bullet list with a table and kept the lock, stale cleanup and run_id staging rules in the steps instead of repeating them.
- Cut the separate Staleness and Trigger tables by folding triggers into each step and the watchdog into one short paragraph.
- Moved setup (seeding the state row) and assumptions into their own section apart from how the system runs; the 60-minute timeout and recon retry-policy notes now sit under assumptions.
- Trimmed the Extract rationale and the recon Purpose, Log identity, Timeout, Compare and False-positives text to the points a newcomer needs; kept the diagram and the SQL unchanged.
- Removed the Q/R-style cross references and the 'see open questions' pointers so each step reads on its own.

### Holes
- Q8: If the load commits at 06:30 after the alert, who or what tells people the dashboards are current again? Does the dashboard show anything to indicate it is showing the previous night? (author: The brief only requires the staleness alert and gives no recovery signal. Nothing in this design tells people when a late commit makes the dashboards current, and the dashboards show no previous-night marker. The data appears at the next dashboard refresh. I added this to Open questions instead of inventing a mechanism.)
- Q12: What does 'page on-call' actually do here? Does a third recon failure page the same way as a third nightly failure? (author: The brief says 'page on-call' but not how. The paging tool and message format are not known and are outside this design. A third recon failure is paged by the same runner in the same way as a third nightly failure, with a message saying it was the reconciliation (that part is decided). I noted in the file that the paging tool is outside the design rather than invent one.)
