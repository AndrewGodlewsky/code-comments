## Review of feat-01 (junior, author haiku, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added a Fixed requirements section that lists the brief's limits (10,000-row threshold, 24-hour link, one active export per user per report, 512 MB worker, 1,800 s timeout, and the rest) so the junior does not depend on a document they cannot see. Replaced references to 'the brief' in Open Questions 4, 5, 8 and 11 with 'the fixed requirements'. Why: the junior asked where the limits come from (Q7).
- Step 1: added a timing check for the 10,000-row small path against the 60-second API limit. Why: Step 4 was at risk and was not measured (Q5).
- Step 3: defined reports.row_count as the unfiltered total written by the nightly rebuild, and linked to Open Question 2. Why: the junior asked what it is (Q2).
- Step 4: stated where the 60-second limit comes from and that the small path reads up to 20 pages in one request. Step 5: stated that it reads no report rows, so the limit does not apply to it. Why: the junior asked about the limit (Q5).
- Step 6: named the existing job queue, the handler name, and its attempt, backoff and timeout values, and that delivery is at least once. Replaced the attempt-start procedure with a single conditional UPDATE shown in SQL. Why: the junior asked how the queue and conditional updates work (Q1, Q6).
- Step 7: the heartbeat is now a conditional UPDATE that requires both the token and state = running. When it matches zero rows, the attempt aborts its own upload and returns without error, so the queue does not retry it. Why: a stopped attempt kept writing after Step 11 (Q8).
- Step 8: added a fence check before complete_multipart, a note on the leftover object that a late complete can create, and the fenced done update in SQL. Why: the junior asked how fenced updates work and what happens at each write (Q6, Q8).
- Step 11: rewritten as a read of upload_id, then one conditional update that repeats the stale rule, then a best-effort abort. Added the effect on a running attempt and a test for it in Step 12. Why: Step 11 did not say what a running attempt does (Q8).
- Open Question 2: added that the rebuild's write order and whether it replaces rows are unknown. Why: the junior asked what the nightly rebuild does (Q3).
- Open Question 10: added the case of a job that waits a long time in the queue before any attempt starts. Open Question 12 (new): who runs the worker processes is unknown. Open Question 13 (new): the storage service behind the exports bucket is not named. Why: these gaps came up in the junior's questions (Q1, Q4).
- Step 5: a stale active export is marked failed by the Step 11 update in the same click, then a new row is inserted. If the update changes no row, the click looks up and returns the active export. Why: Q10 found the old text unclear about what a click does with a stale row.
- Step 6 procedure step 1: the handler's done-case rules are now here, in one place, with the email_sent_at check spelled out. Step 8 points back to it. Why: Q9 found that Step 6 said done returns, while Step 8 said done resends the email.
- Step 2 table: added the links_until column. Why: Q15 found that a link could be issued near the end of the 7-day window and outlive the object.
- Step 7: stated the snapshot gap in full, including what the user gets when row_count stays the same. Why: Q14 asked whether the behaviour was intended, and the old text did not say what the user receives.
- Step 8: record t0 before complete_multipart and set links_until = t0 + 7 days on the done update. The email substep now also sets email_sent_at conditionally. Why: Q15, and to make link expiry safe against the lifecycle rule.
- Step 10: link ttl is min(86400, links_until - now); the endpoint returns expired: true with no URL after links_until, and the page shows expired. The status response no longer depends on completed_at being within 7 days. Why: Q15, and a link issued close to 7 days could otherwise outlive the object.
- Terms used: added job queue (with its settings from jobs.py), attempt and snapshot. Why: Q1, Q11 and Q12 asked what the queue is and what row_count and the rebuild relate to.
- Step 6 starts: the queue's settings are now referenced to the Terms section, and the queue is named as the in-house one. Why: Q1 and Q11.
- Step 12 tests: added the done-with-email-empty resend case, the two-click stale case, and the expired-status case. Why: they cover the changed Step 5, Step 6 and Step 10 behaviour.
- Fixed requirements: added a sentence saying where the limits come from and that the steps enforce them. Why: Q7 asked how the page knows the limits.
- Open questions 6, 8 and 10 were updated to match the revised steps and the jobs.py docstring, and Open question 13 now names link signature verification. Why: Q6, Q8, Q10, Q13 and Q15.
- Step 3 and Step 5: references to Open Question 6 added where the replica and the reports table location are relevant. Why: Q12.
- Step 10 and Step 11: GET latest now runs the Step 11 stale check and returns failed when that update changes the row. Why: a stale running row would otherwise stay running forever when no one clicks (Q16).
- Step 9: on_final_failure now loads the row by export_id to get user_id, report_id and upload_id, and leaves a done row unchanged with no failure email. Why: the payload holds only export_id, and a finished file must not be reported as failed (Q17, Q8).
- Step 6: rewritten as four separate substeps. The old upload_id is cleared in the same conditional update that sets the new token, and the new upload_id is saved with a fenced update. The crash cases are written out. Why: the previous text left the order of the upload_id writes unclear (Q18).
- Step 4: states that the filters and cols alone decide the rows and columns, and that the file may hold fewer rows than the threshold. Adds a 10,000-row cap that returns 503. Why: the junior asked whether filters apply, and a stale row_count must not allow an unbounded buffer (Q19).
- Step 10: the Download button calls the status endpoint again for a fresh link, and an expired response switches the page to the expired state. Why: the previous text had the button fetch a link without naming the request (Q20).
- Step 5: the stale-row branch now says that a successful Step 11 update is followed by an insert in the same request. Added the case where the enqueue has not stored its job_id. Why: the step was ambiguous (Q10, and the queued-without-job_id recovery path).
- Terms: added the primary database, that the queue kills an attempt past the timeout without saying how, and that every conditional update is one SQL UPDATE. Fixed requirements: states where they came from. Why: terms the junior needed were missing (Q6, Q7, Q11).
- Step 8: a done export whose email fails on the last attempt keeps its done state, and the page still offers the download. Added Open Question 14 about the missing email. Why: on_final_failure must not mark a finished file failed (Q9).
- Step 12: added tests for the 10,000-row cap, a filter with few matching rows, the stale GET latest path, and on_final_failure on a done row. Why: these are the behaviours changed above.
- Open Questions 8 and 10 reworded to match the new behaviour; Open Question 13 now says how the signature is checked is unknown. Why: the answers changed what the plan says about links and the final failure.

### Holes
- None.
