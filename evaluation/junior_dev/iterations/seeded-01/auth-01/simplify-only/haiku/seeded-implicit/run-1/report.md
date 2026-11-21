## Review of auth-01 (simplify-only, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Cut the separate draft notes on cookie flags, timeouts and new session IDs. Those rules now sit in the terms, the steps and the notes.
- Merged the draft's login, cleanup and error bullets into four numbered steps. Each step has what starts it, what it does, what data it keeps and where failures are listed.
- Replaced the draft's vague 'Handle DB errors' bullet with a failure table giving what the user sees and what the app does, including fail-closed behaviour at login, protected pages and logout.
- Added the lockout branch, the 401 versus 429 rule, and failure recording on bad credentials and unknown emails to the diagram. The draft's diagram had none of these.
- Stated choices the brief required but the draft did not: Postgres instead of Redis, a 32-byte random hex session ID, per-email counting for unknown emails, a dummy bcrypt check, and hourly cleanup.
- Added one open question for the non-atomic lock race, which the draft did not mention.
- Not done: no junior questions or answers were available to this pass, so these changes come only from the draft and the brief, not from question-driven fixes.

### Holes
- None.
