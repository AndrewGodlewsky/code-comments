## Review of auth-01 (self-review, author sonnet, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Rewrote from a terse outline into a full design that states each choice the brief required: storage (Postgres, with an explicit reason for not adding Redis), expiry check and recording, cleanup, and storage-failure behavior.
- Defined the four tables with columns and purpose, and noted unknown emails are tracked without a users foreign key.
- Added the atomic check-and-renew SQL statement so idle and 12-hour expiry are unambiguous, and specified using the database clock.
- Specified lockout mechanics precisely: sliding 10-minute count, 15-minute lock row, 429 without a password check, success clears failures, and the accepted race.
- Added the identical-response rule for unknown email vs wrong password, including a dummy bcrypt compare for timing.
- Expanded the diagram to cover all flows: lockout, bad credentials, success, valid and invalid protected request, and logout with or without a session. Previously it showed only the happy path.
- Spelled out what 'handle DB errors' means: fail closed with a 503 and a message, with per-flow behavior for login, protected pages and logout.
- Expanded cookie details (opaque ID, flags, no Max-Age, how it is cleared), session ID generation, session-fixation handling and hashed ID storage.
- Replaced abbreviations and fragments ('5 fails / 10 min') with full sentences and added a summary.
- Reworded summary to say what the cookie holds and that state is in Postgres, in plainer terms
- Added one-line lead-ins (tables, failure handling per route) and a sentence explaining the expiry conditions as named limits
- Stated explicitly that failed attempts during a lock are not recorded, and that the lock row is upserted
- Labeled the concurrency caveat as a known limit
- Clarified login_failures.email description and the 'never reaches this point' note
- Tightened wording throughout; no design decisions, SQL or diagram content changed
- Summary: said the session is a row in Postgres, not just 'lives in'.
- Expiry section: added a line explaining that $1 is the SHA-256 of the cookie value, so the SQL is self-explanatory.

### Holes
- None.
