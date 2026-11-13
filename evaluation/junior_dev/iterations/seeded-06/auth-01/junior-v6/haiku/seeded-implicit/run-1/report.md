## Review of auth-01 (junior-v6, author haiku, seeded-implicit)

Rounds: 1. Ended: teachback-correct.

### What changed
- Rewrote the plan in the required order: summary with how the existing system works, terms, explicit choices, diagram, rules, numbered steps, failure table and open questions.
- Chose Postgres for sessions, failure counts and locks, and explained why Redis is not added.
- Specified the lock rule precisely: sliding 10-minute count, 5th failure gets 401, later attempts get 429 with no password check, locked requests are not counted, success clears the count.
- Specified that unknown emails are counted and that a dummy bcrypt check runs, so 429 and 401 responses reveal nothing about accounts.
- Specified session validation as one UPDATE that enforces the 30-minute idle limit and the 12-hour absolute limit, and refreshes last_seen_at on each valid request.
- Specified that every login issues a new random ID and deletes the incoming session in the same transaction.
- Specified the cookie name sid, the raw ID value, and its flags, with no user data in the cookie.
- Specified the cleanup trigger (each instance, every 10 minutes, idempotent deletes) and what each delete removes.
- Specified fail-closed database error handling: 503 on login, cookie kept on protected pages and on logout, and a timeout on each database call.
- Expanded the Mermaid sequence diagram to cover login success, bad credentials, lockout, a protected request and logout, and kept the lock and timeout rules in notes beside it.
- Added open questions for the database timeout value and the per-IP lock risk.
- Added a summary that first says how sign-in works today (none; two instances with no sticky sessions; shared Postgres) and then walks the main flow from start to finish.
- Defined every new term in one plain line: session, session ID, session ID hash, cookie sid, failed attempt, lock, idle and absolute timeout, transaction, upsert, dummy hash, cleanup.
- Kept the four tables and their columns in a Terms section, unchanged in substance.
- Moved the design choices (storage in Postgres and why not Redis, hashed IDs, per-email locks, counting unknown emails, timestamp expiry checks, cleanup cadence, fail-closed errors) into their own Design choices section, each with its reason, as the brief asks for explicit choices.
- Answered the junior's questions in the text: sessions row contents and the cookie value (Q1); how login_locks and login_failures connect and when each row is written (Q2); what a locked user sees and that locks are per email (Q3); the validation UPDATE and the idle refresh (Q4); the identical 401 and the dummy-hash check (Q5); database-error behaviour at each step (Q6); the new session ID and its transaction (Q7); the cleanup trigger and what it deletes (Q8).
- Split the first version's notes into one Rules section and merged overlapping statements (lock rule, count window, the 5th failure getting 401, locked requests not counted, success clearing the count) so each rule is stated once.
- Rewrote the steps so each one says what starts it, what it does, which data it keeps, and what happens when it fails. Step 1 now states the lock check, user lookup, success transaction and failure path in order.
- Kept the Mermaid sequenceDiagram unchanged, with the summary and terms before it and the rules after it.
- Kept the failure table with all eight rows and its wording, and kept the timeout sentence, moving the open question out of it into the Open questions list.
- Cut repetition: the failure table is no longer restated in each step, and the separate 'refused protected requests' and 'logout behaves the same' bullets stay only once in the rules.
- Checked the first version and the brief line by line. Kept: POST /login and lowercase matching; identical 401 text; 5 failures in 10 minutes and 15-minute lock with 429 and no password check; success clears the count; new session ID and deletion of the old session; cookie sid with HttpOnly, Secure and SameSite=Lax and no user data; 30-minute idle and 12-hour absolute timeouts; validation on every request; redirect to /login with cookie cleared; logout behaviour with and without a session; sign-up and password reset out of scope; the 503, 429 and 401 page texts; the 10-minute cleanup cadence; both open questions.
- Did not add any new mechanism, lock, retry queue or rollout section. The brief and first version had no build or rollout content, so none was added.

### Holes
- None.
