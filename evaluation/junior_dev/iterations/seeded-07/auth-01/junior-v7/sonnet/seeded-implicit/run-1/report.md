## Review of auth-01 (junior-v7, author sonnet, seeded-implicit)

Rounds: 1. Ended: teachback-correct.

### What changed
- Spelled out what is stored in sessions, login_failures and login_locks, and that the cookie holds only a random session ID.
- Defined the lock check, the 429 response and its message, and that lockout is per email including unknown emails.
- Defined when failures and locks are written and when failures are cleared (on successful login).
- Defined session validation: database-clock check of 30 min idle and 12 h max, with last_seen_at updated on each valid request.
- Specified login session rotation: old session deleted and new one created in one transaction.
- Replaced 'Handle DB errors' with a fail-closed rule: HTTP 503 plain page, no session created, cookie unchanged.
- Specified cleanup: every 5 minutes on each instance, which tables, and that it is safe to run twice.
- Added the Redis justification: not needed because Postgres is shared by both instances.
- Added the bad-credentials 401 and 'Invalid email or password' wording, and the logout-without-session behavior, which the original notes left implicit.
- Rewrote the summary to say what this is, the main flow and why Postgres-only (no sticky sessions, no Redis).
- Added a terms list: session, sid, cookie flags, the two login tables, fail closed. Folded the table columns and the 128-bit random ID into it.
- Replaced the unordered notes with seven numbered steps (login start, lock check, credentials, success, protected request, logout, cleanup), each with its trigger, action and failure handling.
- Merged the lockout rules, the per-email and unknown-email counting, and the 429 and 401 responses into the steps where they apply.
- Added a failure table, which absorbs the storage-failure note.
- Merged the 'Every page except /login needs this' sentence into the lead-in to the steps.
- Kept all first-version facts: 5 fails in 10 min, 15 min lock, cookie flags, 30 min idle, 12 h max, new ID on each login, cleanup job, DB error handling.
- Left the diagram unchanged. Left out nothing the main flow needs; the exact 429 and 503 page wording stays, and library and format choices stay out.

### Holes
- None.
