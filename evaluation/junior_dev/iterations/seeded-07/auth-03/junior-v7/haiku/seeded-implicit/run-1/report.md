## Review of auth-03 (junior-v7, author haiku, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added a summary of how the existing system works today and what the reset adds, before the diagram.
- Added a terms section that defines token, SHA-256 hash, session, email queue, email worker, breached-password list and row lock.
- Replaced the placeholder 'usual retries' with the brief's rule: one try plus up to 3 retries with backoff, then the job is dropped and nobody is told.
- Stated the exact generic reply text and that it is the same for unknown addresses and for requests over the limit.
- Stated that the rate limit counts reset_tokens rows per account in a rolling hour, using a row lock so two requests cannot both pass the limit.
- Stated what reset_tokens stores, what the emailed link carries, and that older unused tokens are marked used when a new one is made.
- Stated that the token is checked on page load and again on submit, and how the form carries the token.
- Moved the password check before the transaction, and made the token claim the first step inside it, so a failed password check never uses up the link.
- Stated that the breached-password check fails closed when it cannot run.
- Stated that revoking sessions deletes every sessions row for the user, including the resetting device, and that the user is redirected to login without a session.
- Added failure handling at each step, rather than a separate table, so each failure sits next to the step it belongs to.
- Added open questions for per-IP limits, the silent drop after retries, the unknown queue technology, reply timing, the breached-password check's form, and the lost confirmation email.
- Step 1 is now one database transaction (lock, count, kill older tokens, insert, queue job, commit), so the row lock holds until the job is queued (Q10).
- The link email job is queued inside the step 1 transaction, so a failed queue write rolls back the token row and it does not count toward the limit (Q11).
- Step 1 failure handling rewritten to match the single transaction, with a server error for any address and a full rollback.
- Notes corrected: steps 3 and 4 check the token, not step 1. The first version wrongly said step 1 checked it.
- Diagram step 1 line updated to show the transaction and commit before the reply.
- Added a What happens when things fail table, so the failure paths sit in one place.
- Added an open question: a queue failure returns a server error only for known addresses, which may conflict with the brief's always-the-same reply.
- Open question on the queue technology now also says it decides whether the queue write can share the database transaction.
- Summary: rewritten to 4 short sentences. It now first says how today's system works (web client, API, Postgres, email queue and worker), as the skill asks, and says the reply does not wait for the email.
- Terms: added definitions for token, SHA-256 hash, reset_tokens, link check, rate limit, users, sessions, email queue, email worker, mail provider, backoff, row lock, hidden field and breached-password list. Each is one plain line. Everyday words such as transaction are not defined.
- Merged the repeated link-validity rule (exists, unused, under 30 minutes old) into one 'link check' term. Steps 3 and 4 refer to it instead of restating it.
- Merged the old diagram, steps and notes into one short diagram plus numbered steps. The diagram shows the flow; the steps add only what the diagram cannot show: start trigger, what is kept where, and failure handling.
- Moved each note to the step it applies to: no-account skip and generic reply to step 1; queue write inside the transaction to step 1e; token re-check at submit to step 4; 'no session created' to step 4f; the 'fails closed' rule to step 4c.
- Added the reasons the Q&A answers gave, each in one clause: why the lock (two requests could both count 2 and pass the limit), why the queue write shares the transaction (a rolled-back row does not use a slot), why the link is checked at page load (so a dead link never shows a form), why the token is re-checked at submit, and why revoking sessions logs out the current device.
- Added the job contents (recipient, email type and link), the worker's one try plus up to 3 retries, and the reason the rate limit counts per account (the brief says per account, and each link creates one row, so no counter table is needed).
- Kept every stated requirement and number from the brief and first version: generic message text, 3 per rolling hour, 32-byte token, SHA-256 storage only, 30-minute expiry, single use, killing older links, 12-character minimum, breached-list check, the logout of all sessions, the password-changed email, the redirect to login with no auto-login, and the retries with backoff.
- Failure table: all nine rows kept, with step labels reworded (for example '4a' for the token check) so no reader has to look elsewhere. Wording of each result is unchanged.
- Open questions: all eight kept and reworded in plain sentences. None were answered or dropped.
- No build or rollout section was added because the brief and first version contain none. The 'Today' sentence does not change the plan's intent.
- Terms: the email queue is now described as assumed to be a Postgres table, with a pointer to open questions, instead of stated as fact.
- Diagram: added one line after it saying the queue table in the Postgres box is assumed.
- Step 2: the worker now deletes the job after a successful send or a final drop, so the raw token does not stay in the queue (Q13).
- Step 2: stated that a failed reset link still counts toward the limit, because its row was committed in step 1.
- Step 3: stated that the link is a web-client address with the token as its last part, and that the page reads the token from its address (Q15).
- Steps 3 and 4a: stated that the expired page gives no reason, and that a replaced link gets the same page (Q16).
- Step 4e: stated where the recipient comes from (users, by user_id) and that the email uses the same queue, worker, retries and drop rule (Q17).
- Failure table removed. Each step now says what happens when it goes wrong, so each fact appears once.
- Duplicate sentence about the job and token being written together was merged into step 1e.
- Open questions: added the conflict between the never-store-the-raw-token rule and the queued link (from Q13), the possible duplicate send after a crash (Q14), and the conflict between step 1's server error and the brief's 'always returns the same message' rule. Also added the link host and path and the email wording to the not-decided list.
- Summary: shortened to three sentences that say what the feature is, the main flow, and why it is shaped that way.

### Holes
- Q12: The Terms and diagram say the queue is a Postgres table, but the first open question says this is unknown. Is it decided or only assumed? Which should I rely on when explaining step 1? (author: The brief does not say the email queue is a Postgres table. The first version's terms and diagram assumed it. I cannot confirm it from the brief, so step 1 is explained on that assumption, and the document now says it is assumed. If the queue is not Postgres, step 1 changes, and this is the first open question.)
- Q14: If the worker crashes or times out in the middle of a send, is the job picked up again? Could the user get the same email twice? (author: The brief does not decide how a job is marked taken or finished, so I do not know whether a job is picked up again after a crash. If the worker crashes after the mail provider accepts the email but before the job is deleted, a retry could send the same link twice. The link works once, so only one copy can be used. This is listed under open questions.)
