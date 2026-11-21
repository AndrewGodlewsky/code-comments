## Review of feat-01 (junior-v2, author haiku, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Terms: added the queue, the enqueue call, the 1,800 s attempt timeout and the retry schedule, and a definition of the export record (Q1).
- Step 3: merged the permission check into step 3.1, and moved the bounded replica count into the main flow as step 3.4 with its routing to step 5 (Q7).
- Step 5.1: listed both stale-row rules explicitly, the queued row without job_id after 5 minutes and the running row older than 2 hours, and said queued rows with a job_id are never stale (Q2).
- Step 6: stated that the job reads filters and cols from the export record, and that step 6.1 continues for queued or running rows (Q3, Q4).
- Step 6.3: stated that a retry finds the row running and passes the conditional update (Q4).
- Step 7: stated that rows are filtered and ordered by the saved filters and cols through the step 1 module (Q3).
- Step 9: explained the ttl calculation and that the signed URL is served by object storage (Q8).
- Step 10: noted that if the status write fails and the row stays running, no email is sent, and step 5.1 clears it (Q2).
- Step 11: defined latest as newest created_at, stated that a new export after a failure is a new row, and that filters are returned so the page can say which filters were used (Q5).
- Open questions: moved the stale-count guard reference to step 3.4, and added open question 8 for overlapping deliveries and open question 9 for where the permission record lives (Q6, unresolved).
- Simplified: merged the duplicate description of the export record into the Terms, shortened the repeated attempt and retry wording, and removed the separate open-question prose from steps 3 and 5. The document is slightly shorter than the previous version.
- Fixed the title line: the literal `\n\n` sequences in the draft are now real Markdown headings (Summary, Terms, Steps, Open questions).
- Terms: merged the queue's timing, retry and at-least-once notes into one bullet, and shortened the keyset and multipart definitions. The terms are still needed by steps 6 to 8 and open question 8.
- Step 1 and step 3: shortened the wording of the shared-module and permission-check rules. No check or order changed.
- Step 4: merged the response headers and the streaming work into one data-moves line.
- Step 5: merged the two 'if it fails' sub-bullets on the 503 and the dead process into shorter lines. The stale-row rules, the 200 reuse path, and the post-commit enqueue are unchanged.
- Step 7: merged the memory and time notes into the 'State kept' and 'If it fails' bullets. The 16 MB buffer, 5,000-row batches and the 1,100 rows/s budget are unchanged.
- Step 11: merged the 'Starts' line with the 'Data moves' line and cut repeated phrasing in the display list. The five display states and polling rules are unchanged.
- Steps 12 and 13: trimmed the test wording and merged the alert and count lines in step 13. Every test named in the brief is still present.
- Open questions: trimmed each to one or two sentences. All nine are kept, in the same order, so the references to them (1, 2, 4, 5 and so on) still hold.
- Kept every step number and sub-step number, so the cross-references (3.4, 5.1, 6.1, 6.2, 6.4, open questions 1 to 9) still hold. No behaviour was changed.

### Holes
- Q6: What do permission records and report.view look like, and who answers the check? Is it a function that reads the permission record on the primary? (author: The brief's files say the API checks report.view and returns 403 otherwise, but they do not say what the permission record looks like or which database it is read from. I did not invent a store. Step 3 says only that it uses the same check as the page API. Open question 9 records this.)
