## Review of auth-03 (junior-v5, author haiku, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added step 1.4 for token creation: 32 CSPRNG bytes, base64url, only the SHA-256 hash stored, raw token only in the email job (question 1).
- Added Outbox row and Relay terms, and made the queue-in-Postgres choice explicit in step 1.6, because the brief does not say where the queue is stored. Made it open question 1 (question 2).
- Added a Worker note covering the pre-send link check, deleting the job on success, 3 retries with backoff, then log and drop. Added the revoked-job case to the failure table (question 3).
- Step 1.5 now says it runs only when the limit allows a new link, and a note explains that over-limit requests leave the existing link valid (question 4).
- Added a note explaining why the token is checked at steps 3.1 and 3.4 (question 5).
- Added a sessions note: the reset creates no session and each device must log in again after it. Noted that session-row matching is outside this design (question 6).
- Step 1.3 now says the count covers active, used and revoked links. Added that the over-limit user sees the same generic reply (question 7).
- Cleanup of rows older than 24 hours is marked as not decided, with the simplest option named. Moved to open question 2 (question 8).
- Replaced the D1 to D9 codes and the step letters with plain-language rows in a failure table, and numbered the diagram steps as 1.1 to 3.4.
- Added a summary and a terms list before the diagram. Moved the four review decisions into open questions 3 to 6 and added question 7 for the unknown-address timing.
- Removed the sentence that said the retry-job check is a re-check of state only, and stated it as a single rule in the worker note.
- Cut the section labels and cross-references such as A., C., D2, Q5 and R3, and used plain step numbers and plain names. Each step is now explained in its own sentence, so no reader has to look elsewhere.
- Moved the rate-limit notes into steps 1.2 and 1.3, the one-active-link note into step 1.5, and the email-job and outbox notes into step 1.6. Each step now gives what starts it, what it does, what data it touches, and what happens when it goes wrong.
- Merged the 'Same reply every time', 'Link previewers' and 'Rejected passwords' notes into the steps that they concern. Removed the separate 'Clock' note and folded the database-clock fact into the Data section.
- Merged the two token-exposure notes (URL in logs and Referer, and link previewers) into one short 'Token in the URL' paragraph. Kept the header and body rules for the token.
- Added a reason clause where a part appears: why the raw token is made after the limit check (step 1.4), why the link is checked twice (step 3.4), why the reset creates no session (step 3.4), why revoke happens only on issue (step 1.5), and why opening the link is read only (opening section).
- Added plain definitions for terms the reader needs: transaction, relay, SHA-256 fingerprint, CSPRNG, argon2id, breached-password list, backoff, Referer header and foreign key. Defined the relay as doing nothing else, as the answers stated.
- Stated the session matching as outside the design, and that the cache, if any, is cleared in step 3.4, as the answers stated.
- Kept the diagram in its original form and step numbers, with minor wording edits, and kept the summary and terms before it and the notes after it. Kept the failure table and all seven open questions unchanged in substance. Open question 1 (queue storage) and open question 2 (cleanup) remain open, as the answers said they must.
- Clarified the Data section: the rate-limit window is one hour, so the 24-hour cleanup never removes a row the limit needs. Also listed the two changes to existing tables (users.password_hash and sessions rows). Nothing in the design changed; these lines only state what it already did.
- Merged the lookup (old step 1.1) and the row lock (old step 1.2) into one step 1.1 inside one transaction, so a user deleted in between cannot be missed (Q15). Request steps are renumbered 1.1 to 1.6.
- Worker step: a missing or inactive or expired link row now means drop the job with no retry (Q10).
- Worker step: a job is deleted when it is dropped after the third failure as well as on success, so the raw token leaves the queue in both cases (Q9).
- Step 1.5: the job becomes visible only at commit, so the worker cannot take it earlier (Q10).
- Step 3.2: a rejected password re-renders the form with the same token in the hidden field (Q13).
- Data section: says where the raw token is kept and that it conflicts with the brief (Q9). Added open questions 8, 9 and 10 for the raw-token conflict, the login race and the login-page notice (Q9, Q11, Q12).
- Summary: now explains how the existing system works before the new flow, as the skill requires. Terms: added the Link term and tightened the wording of the others.
- Failure table: added the login-race row and changed the wording of the stale-job row to match the worker step. No new mechanism was added, and the request, submit and cleanup behaviour is unchanged.
- Step 3.1 now keeps the link's user_id for the later users-row lock.
- Step 3.4 (diagram and text) now locks the users row first, then the password_resets row, the same order as step 1.1. This removes a deadlock between a reset request (users, then password_resets) and a submit (password_resets, then users).
- Failure table: the two-submits row now names the users row lock, and a new row covers a reset request racing a submit for the same account.
- Token in the URL: defined what stripping the token from logs means and which logs it covers, with the replacement written as /reset/[redacted].
- Mail worker: the link check now runs before every send attempt, including each retry, and a retry after expiry sends nothing. Added a matching failure-table row.
- Step 2.2: the expired page is the same for all non-active cases, and its 'request a new one' link goes to the Forgot password form.

### Holes
- Q2: Is the email queue stored in Postgres in this design? D9 and the Outbox note mention a 'relay', but the diagram never shows one. What is it and what does it do? (author: The brief says outgoing mail goes through an email queue that the API adds a job to. It does not say whether that queue is stored in Postgres. The relay is needed only if it is not. The design writes an outbox row in the same transaction and a relay copies it to the queue. The relay does nothing else. Added to open questions as question 1.)
- Q8: What deletes rows older than 24 hours, and what runs it? (author: Nothing in the brief or the earlier design says what runs the cleanup of rows older than 24 hours. The design needs a cleanup job, but I have not chosen one. The simplest option is a daily scheduled DELETE, if the stack has a scheduler. Added to open questions as question 2.)
- Q11: In step 3.4 the password_resets row is locked, but users and sessions are updated in the same transaction. If a login happens at the same moment as the reset, can a new session row survive the DELETE? (author: The brief does not say whether login locks the users row before it creates a session. If it does not, a login that checked the old password just before the reset can commit a session row after the reset's DELETE, and that session survives. The design does not stop this. Recorded as open question 9. A fix needs the login path, which is outside this design.)
