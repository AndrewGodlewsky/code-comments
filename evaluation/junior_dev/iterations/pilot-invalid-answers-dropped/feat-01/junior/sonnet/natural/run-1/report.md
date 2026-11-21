## Review of feat-01 (junior, author sonnet, natural)

Rounds: 3. Ended: cap.

### What changed
- Added an 'Existing pieces' table (row_count, rows API, job queue, storage helpers, send_email) so the document explains the helpers it calls and who calls on_final_failure (Q1, Q4, Q8).
- Defined that a NULL or missing row_count means unknown and takes the large path, and described how fresh row_count is (Q1).
- Added a response-shape table for the POST (200 text/csv, 202 JSON, 200 JSON with already_active) and how the page tells them apart (Q2).
- Stated in step 4 and Decision 1 that a click with different filters gets the active export and must wait, then click again (Q3).
- Step 3 now describes how the page saves the CSV (fetch, Blob, download link) and how it handles JSON responses (Q9).
- Step 5: the orphan-repair check now also runs from the status GET and uses a conditional UPDATE to claim the row, and the never-returns case is documented. Step 11 and step 13 tests were updated to match (Q6).
- Step 10: explained that the queue detects dead attempts, what the row and page show between attempts, and the worst-case duration (Q5).
- Step 6: showed the @job registration with on_final_failure and the role of ctx.attempt (Q4).
- Step 7: named the shared build_rows_query function, said it needs only stored filters and cols and no session, and added Decisions 5 (unverified assumption) and 6 (email templates) (Q7, Q8).
- Step 6: replaced the unconditional 'set running' with an atomic conditional claim (attempt < ctx.attempt) so simultaneous duplicate deliveries cannot both run, and made later writes conditional on the attempt number (Q10).
- Step 6: stated that the queue does not start attempt N+1 until N has ended, and added a Limit note about same-attempt redelivery after a worker death.
- Step 5: changed the double-enqueue remark to point at step 6's claim instead of 'safe to run twice'.
- Step 8 and 9: made the done update conditional on attempt, and noted the email-only path can send a duplicate email; removed the now-redundant duplicate-delivery bullet in step 8.
- Added an Error row to the response-shapes table and a new table of page messages for 400, 403, 500/503 and network failure; updated steps 2 and 3 to refer to it (Q11).
- Step 3: explained the 45 s stop as an elapsed-time check between pages, noting its limits (Q12); removed the duplicated replica-error line from the page text.
- Step 1: clarified that attempt is set by the claim in step 6.
- Step 13: added tests for error messages and for two simultaneous copies of the same attempt.
- Decisions to confirm: added item 7 (queue redelivery semantics) and item 8 (per-query timeout), both unknown.
- Step 3: added a 10,001-row cap on the small path that discards the partial CSV and falls through to the large path, because row_count can be a day stale (Q13).
- How it works and row_count table row: described the stale-row_count behaviour (stale-low caught by the cap, stale-high goes to the job) so the file itself answers Q13.
- Step 4: 'Starts when' now includes the step 3 cap fall-through, so the flow is consistent.
- Step 3: added a short consistency note about the rebuild overlapping the small read (Q14).
- Step 7: added a 'Data consistency (the nightly rebuild)' paragraph stating exports are not snapshots, retries can differ, and the rebuild mechanism is unknown (Q14).
- Step 2: spelled out that otherwise the small path is taken, for clarity.
- Step 13: added a stale row_count test (9,990 stated versus 10,400 actual).
- Decisions to confirm: added item 9 on the nightly rebuild versus a running export, flagged as unknown with possible mitigations.

### Holes
- None.
