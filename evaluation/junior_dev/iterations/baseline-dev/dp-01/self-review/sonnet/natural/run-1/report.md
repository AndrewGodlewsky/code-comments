## Review of dp-01 (self-review, author sonnet, natural)

Rounds: 3. Ended: passes.

### What changed
- Rewrote the summary as a three-step outline (extract, stage, commit) and stated the overlap/idempotence idea up front.
- Added a 'Terms used below' section defining HWM, lookback, soft delete and run_date, so a reader new to the project can follow.
- Added a one-line reading guide above the flowchart.
- Fixed an inconsistency: the old text said staging rows were dropped on failure and also at the start of each attempt. Now a failed attempt may leave rows, and the next attempt deletes them before loading. Flowchart, prose and table agree.
- Flowchart: shortened labels, renamed 'deduped rows' to 'staged rows' (dedupe happens in the commit step), made the retry edge say 'new run_id, same HWM', and sent reconciliation failure to PAGE only on the third failure.
- Made the 06:00 check wording consistent ('today's run_date') and explained that a retry keeps its run_date.
- Explained the run lease in one sentence and why the late-row reconciliation exists.
- Renamed 'Merge, in one transaction' to 'Commit, in one transaction' and removed a vague lead-in sentence.
- Reordered the staging bullets to put the reason staging is outside the transaction first.
- Moved the Terms section ahead of the flowchart so HWM, lookback, run_date and soft delete are defined before they appear in the diagram.
- Added 'Attempt' to the terms and clarified that each attempt has its own run_id.
- Replaced the flowchart intro with a short statement of what starts work, and removed the duplicate 'three triggers' sentence.
- Reworded the Summary to state that retries are the only other starts of work.
- Added the missing subquery alias (ranked) so the SQL is valid.
- Clarified the checksum wording (sum over the day's rows) and the reason the staging load is outside the commit transaction.
- Small wording tightening in several bullets; no change to the design or content.
- Replaced the 'Three things start work' paragraph with an explicit bulleted list of what starts work, including retries.
- Added 'Upsert' and 'Run lease' to Terms and moved the run lease definition up so it is defined before use; reordered Attempt before run_date.
- Clarified that only the commit step reads staging in the Summary.
- Clarified staging cleanup: the next attempt deletes all leftover rows from earlier failed attempts, safe because of the run lease.
- Tightened wording in the flowchart intro and state section (read or written; lease sentence).
- Left the flowchart, SQL, and tables unchanged in substance.

### Holes
- None.
