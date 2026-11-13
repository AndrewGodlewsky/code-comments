## Review of auth-01 (rewrite-v7, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Cut: merged the separate Decisions list into Stored data, Steps and Rules, so each fact appears once.
- Cut: removed the repeated lock, cookie and expiry text that appeared in both the decisions and the diagram notes.
- Added: a Summary of the current system and the change, then a Terms section with one-line definitions for every term a newcomer would not know (Postgres, session, cookie, cookie flags, hash, CSPRNG, bcrypt, dummy hash, enumeration, row lock, idempotent, database clock, sticky session, 303, no-store, Retry-After, CSRF, cleanup job).
- Added: a Stored data section listing the three tables, their columns and indexes, and what email_key means.
- Changed: the diagram's no-cookie branch for protected requests now clears the cookie, because the brief (requirement 7) says a missing session clears it. The original diagram did not show this.
- Changed: steps for sign-in, protected page and sign-out, each saying what starts it, what it does, which data it keeps and what happens on failure.
- Moved: local HTTPS development and the 72-byte password check to a separate Build and rollout section, apart from how the system runs.
- Moved: the Redis rationale to its own short section, with the revisit condition kept.
- Added: a failure table that includes the locked-account 429 and the missing-session redirect, alongside the storage failure rows.
- Kept: every requirement, limit, number and rule from the first version and the brief, including the 254-character email limit, the 72-byte password limit, the 5-failure, 10-minute and 15-minute lockout values, the 30-minute idle and 12-hour absolute limits, the 15-minute cleanup cycle and its one-day and 10-minute thresholds, the Retry-After values, the three open items, and the per-email serialization and tradeoff.

### Holes
- None.
