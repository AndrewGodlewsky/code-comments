## Review of auth-03 (junior-v2, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Moved the token check ahead of the password check on submit, so an expired link is reported first (Q5).
- Removed the dummy-hash note and recorded the timing gap as open question 5 (Q3).
- Defined the worker's pre-send check, its skip versus retry rules, and the link format (Q2, Q7).
- Stated why the encrypted token stays in the job, and how the worker decrypts it (Q1).
- Removed the session-cache row from the failure table and moved it to open question 4 (Q8).
- Merged the unknown-address and over-limit failure rows, redrew the diagrams to fix misaligned boxes, and removed the decided raw-token question from the open list (Q1).
- Section 2, step 1: the email rule is now stated as trim and lower-case, matching the login lookup (Q10).
- Section 2, step 4: the "no" branch is labelled "skip to step 5" so the diagram shows where the request ends when no token is written (Q9, simplicity).
- Section 5: the email job now has two kinds, reset (with token fields) and password_changed (with user_id only), so the notice has a defined payload (Q9).
- Section 5: the 24 h purge now names its runner, its reason, and what a user sees when a link's row has been purged (Q11).
- Section 6: added the rule for password_changed jobs (look up the address by user_id, no superseded check) (Q9).
- Section 6: added the crash-after-send rule: a possible duplicate send is accepted because the link is still single-use (Q12).
- Section 7: added open question 7 for the queue's claim rule, which is unknown (Q12).
- Section 2: merged the 'no user: skip' and 'fewer than 3 tokens' checks into one skip condition at step 3, so the diagram has one branch to step 5 instead of two.
- Section 2: merged the rate-limit and concurrency notes into one note, and dropped the duplicated 'every branch returns the same 200' phrasing from the earlier notes.
- Section 3: defined 'valid token' once, before 3a, and referenced it from 3a and 3b. The same three-condition test had been written out in full in both diagrams.
- Section 3b: shortened the diagram labels for the password check and the re-check under the lock. The steps and their order are unchanged.
- Section 3b notes: cut the sentence restating that the expired page is shown at once. The step order already shows it.
- Section 4: merged 'Link already used or revoked' into the expired-link row, and merged 'Provider outage' into the 'Send fails 3 times' row, since both behave the same. Removed the 'expires_at fixed at issue' detail, which section 5 already states.
- Section 5: compacted the token table definition and the users/sessions bullets. Merged the email-job notes (deleted when sent or dropped, logs hold no token) into the job list.
- Section 5: shortened the purge rationale and the encrypted-token rationale. The reasons are kept, and the duplicate timing argument was removed.
- Section 6: kept the worker steps unchanged. Merged the retry and skip rules into one bullet, and shortened the duplicate-send explanation.
- Section 7: kept all seven open questions together at the end with their numbers unchanged, so the references in sections 2, 3b, 4 and 6 still resolve. Shortened the wording of questions 1, 3 and 7 without changing what each asks.
- Kept the intent and the fixed brief requirements: the 3-per-hour limit, the 30-minute single-use link, the revoke on reissue, the hash-only storage, the two-step check on submit, the lock and the logout on every device. No new mechanism was added.

### Holes
- Q8: What do 'sessions' hold, and how does the API use them for each request? What is the 'session cache in API (if any)'? (author: A sessions row is one logged-in device. The API checks it on every request, as the brief says. The brief describes no session cache, so I do not know whether the API caches sessions. The design says to invalidate the cache on delete if one exists. This is open question 4.)
- Q12: How does the worker claim a job from the queue, and what happens if the worker crashes after sending but before deleting the job? (author: I do not know how the existing queue claims a job, such as by lease or visibility timeout, because the brief names the queue but not its claim rule, and I have not read its code. Decided part: if the worker crashes after sending and before deleting the job, the job may be sent again. This is accepted, because the resend carries the same single-use link and has no security effect. Section 6 and open question 7 now say this.)
