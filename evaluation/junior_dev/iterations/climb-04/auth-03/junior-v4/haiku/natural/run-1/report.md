## Review of auth-03 (junior-v4, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a summary, terms and notes so the flows read in order from the top.
- Flow 1: numbered the steps, made the unknown-email branch explicit, and stated that the hourly count includes used and invalidated rows.
- Renamed 'outbox' to 'email queue' to match the brief; an email job now has a type, and only reset-link jobs carry a token.
- Flow 2: the live check reads the reset row by id; password-changed jobs skip it; the encrypted payload is cleared on send or drop.
- Flow 3: stated that GET is read-only; moved the password check and hashing before BEGIN; stated that the reset row lock prevents double submits.
- Replaced the session created_at check with a login row lock and removed password_changed_at, because the timestamp check did not close the login race (a session created after the reset has a later created_at and would have been accepted).
- Changed the timing claim from 'keep close' to an accepted difference, now open question 8.
- Moved open issues to the end, shortened them, and added open questions 7 (queue location and worker pickup) and 8 (reply timing).
- Cut the purge rationale to one line and merged repeated retry text in the failure table.
- Flow 1, step 4: the email job line now names user_id, so the worker can find the account.
- Flow 2 diagram: the send step now says the address comes from the users row by user_id.
- Flow 2 notes: added a bullet stating that both job types send to the stored account address, read at send time, and that the job holds no address.
- Data section: the email job line now says the job holds no address and the worker reads it from users.
- Summary rewritten to say how the existing system works today (session checks, email queue, 3 retries then silent drop) before the new flow.
- Terms list now defines the terms a newcomer needs: token, reset row, live, email job, app key and session. Removed the duplicate statements about rows staying after use and the job holding no address; each now appears once.
- Flow 1 steps are numbered to match the diagram and each states what starts it, what it does, what it keeps and what happens on failure. The reply-timing and no-user notes are folded into the steps.
- Flow 2 and Flow 3 steps are rewritten in the same format. The 'reads only' reason for the link GET and the 'hash before the transaction' reason are kept inside their steps.
- Login locking note moved into its own short section after the steps, since it changes the existing login flow.
- Added a failure row for a database error while requesting a link (full rollback, nothing queued, server error). The first version had no handling for this. This is a new simplest-handling choice, not a change of plan; it needs review.
- Removed number cross-references ('see open question 7', 'open question 1') from the body. The open questions stand alone at the end.
- Data section kept as a short list. It now says the encrypted token is cleared with the rest of the payload when the job is sent or dropped.
- Open questions kept (8 items). Question 1 still needs sign-off. The wording for question 7 now says the queue must be in Postgres for the same-transaction write to hold.
- Both diagrams kept as they were, since the skill requires the diagram form to stay.

### Holes
- Q2: What does the email worker read from, and how does it get started? Is it polling the outbox table, and how does it know a job is ready? (author: The brief does not say how the email worker finds new jobs (polling, notification or an external queue) or whether the queue is a Postgres table; the design assumes Postgres so the job can share the reset row's transaction (open question 7).)
