## Review of auth-01 (simplify-only, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered into summary, terms, tables, diagram, numbered steps, failure table, open questions.
- Added a short opening on how the system runs today (two instances, no sticky sessions) and why Postgres instead of Redis.
- Merged the scattered notes (lockout, cookie flags, timeouts, new session ID, cleanup, DB errors) into the terms and steps.
- Replaced vague 'Handle DB errors' with one rule and a table: fail closed, 503, no retries.
- Replaced the flat diagram with one that shows the lockout and bad-credential branches, the expired-session path, and the 429 and 401 responses.
- Made each step state its trigger, action, data and failure handling.
- Merged bad-credentials handling into one step covering both unknown email and wrong password.
- Kept cleanup as a single idempotent hourly delete and said it never decides expiry.
- Left one open question on whether a failed logout should clear the cookie.

### Holes
- None.
