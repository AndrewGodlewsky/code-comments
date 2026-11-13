## Review of auth-01 (rewrite-v7, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Wrote the opening summary: what exists today, why Postgres (shared by both instances, avoids adding Redis), and the main flow.
- Added an Existing system section and a Terms section (session, sid, idle and absolute timeout, failure count, lockout) that the first version lacked.
- Added concrete table columns for sessions, login_failures and login_locks, and the exact expiry rule checked on every read.
- Turned one-line notes (lockout, cookie flags, timeouts, bad login, new session ID, cleanup, DB errors) into numbered steps and shared rules; kept every number: 5 fails, 10 min, 15 min lock, 30 min idle, 12 h max, HttpOnly/Secure/SameSite=Lax.
- Expanded the diagram to cover lockout (429, no password check), bad credentials (401 and failure/lock recording), deleting the old session on login, clearing failures on success, redirect to /dashboard, and logout with no session.
- Added requirement details the first version dropped: lowercase emails, identical 401 for unknown email and wrong password, 429 without password check, dummy bcrypt check to avoid timing leak, destroy incoming session on login, logout before reply and same with no session.
- Decided the cleanup job (every 10 min per instance, idempotent, only saves space) and the storage-failure behavior (fail closed with 503; cookie kept on protected pages and logout; no session created on login).
- Added a failures table and a note accepting a small race across two instances at the lockout limit.
- Added Open questions: IP-based rate limiting and extra CSRF protection are out of scope.
- Cut nothing from the stated facts; the first version's vague 'Handle DB errors' and 'Cleanup job' were replaced by explicit choices.

### Holes
- None.
