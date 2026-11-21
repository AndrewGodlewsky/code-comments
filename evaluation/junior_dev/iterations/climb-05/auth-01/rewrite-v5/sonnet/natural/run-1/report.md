## Review of auth-01 (rewrite-v5, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Rewrote in the skill's order: summary paragraph (today's system, main flow, why Postgres-only), terms, schema, diagram, notes, failure table, rollout, out of scope, open questions.
- Replaced the large Decisions table with the summary paragraph and a Terms section; moved each reason into the clause or note where the part appears (Redis rejection, hashed ID, browser-session cookie, database clock, cleanup job).
- Added plain one-line definitions for session, session ID, idle and absolute limit, failure row, lockout, advisory lock, fail closed, and database clock.
- Merged the Expiry, Cleanup, Cookie and CSRF bullets into shorter notes; merged the two rows of identical-response rules; dropped repeated statements such as 'all deletes safe to repeat' details and the 'no failure path returns a protected page' bullet.
- Removed the 'step 15' cross-reference; the note now says a successful fifth attempt clears all failure and lockout rows.
- Added a short Rollout section to keep how it runs apart from how it ships, and an explicit pointer that other failures are covered in the flow.
- Added a one-line note that the existing users table is unchanged and that sign-up and reset are out of scope.
- No design changes: all behaviour, schema, diagram and failure handling are kept as originally written; no junior questions were supplied so none were added or dropped.

### Holes
- None.
