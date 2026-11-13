## Review of feat-01 (junior-v1, author sonnet, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Facts section: noted the primary-read rule has no documented reason, row_count is the unfiltered nightly total read from the same replica, and added what ctx contains and that timeouts and dead workers also retry and reach on_final_failure.
- Step 2: stated that row_count is unfiltered so filters never change the path.
- Step 4 and step 5: moved the repair of a queued row with NULL job_id into the status endpoint so it heals without another click (fixes a stuck disabled button).
- Step 6: said the page shows running during backoff waits and that the handler reads ctx.attempt.
- Step 7: added a first item re-parsing filters and cols with the rows API parser, and what happens if it rejects them.
- Step 8: replaced the invented address lookup wording with an assumption about send_email, and said where report_name and expires_at come from.
- Step 11: added a failure-injection check for the API dying between insert and enqueue.
- Open questions: added the undocumented reason for the primary-read rule, the unknown speed of killed-attempt detection, and which process writes row_count.

### Holes
- Q1: What is the rule against reading report data from the primary, and why does it exist? Also, what does the replica lag mean for a user who clicks right after the nightly rebuild? (author: The existing docs say report data must never be read from the primary but give no reason, so I do not know why the rule exists. I treat it as a given and follow it. For lag after the nightly rebuild: row_count and the rows both come from the replica, so they agree with each other; what a user sees during replication catch-up is not documented. Both added to the file (facts section and open questions).)
- Q4: When an attempt times out at 1800 seconds or the worker dies, does the queue still retry and call `on_final_failure`? Who notices a killed attempt, and how long does that take? (author: Per jobs.py, an attempt fails if the handler raises, times out or its worker dies, and failed attempts retry after the backoff until 3, then on_final_failure is called once. That covers timeouts and dead workers. How long the queue takes to notice a dead worker is not documented, so the 5.1 hour worst case is a lower bound. Added to facts and open questions.)
- Q6: What does `send_email(user_id, template, data)` do exactly? Where does it get the address, and where do `report_name` and `expires_at` come from? (author: The brief only gives the signature send_email(user_id, template, params). I do not know how it finds the address; I assume it resolves it from user_id and flagged that in the file. report_name comes from the report's record (column name not verified), and expires_at is the send time plus 24 hours, the same ttl given to signed_url. I removed my earlier wording that implied we look up the address ourselves.)
