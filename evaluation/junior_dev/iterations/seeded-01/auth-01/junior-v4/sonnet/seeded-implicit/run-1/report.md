## Review of auth-01 (junior-v4, author sonnet, seeded-implicit)

Rounds: 1. Ended: teachback-correct.

### What changed
- Replaced the vague bullet notes with defined terms and table columns (sid contents, sessions, login_failures, login_locks).
- Added the lockout branch (429, no password check), the bad-credentials branch (401, record failure, maybe lock) and the success branch to the diagram.
- Added the expired/missing session branch with row deletion and the valid branch that refreshes last_seen_at.
- Stated expiry rules: 30 min idle via last_seen_at, 12 h via created_at.
- Stated the lock is keyed on lowercase email only and counts unknown emails, to keep responses identical.
- Spelled out that login deletes the old session and issues a new ID.
- Replaced 'Handle DB errors' with a per-step 503 table and a fail-closed rule.
- Defined the cleanup job: hourly, per instance, idempotent, three tables.
- Added a short opening on how the system works today and why Postgres rather than Redis; removed the vague 'Open questions' gap since all items are now decided.
- Added a short opening section on what the plan is and how the main flow goes, replacing the old intro paragraph.
- Merged the separate cookie-flags bullet into the sid term.
- Moved the terms before the diagram under clear headings (What this is, Terms, Flow).
- Folded the storage-failure rule into a section named 'When Postgres fails or is slow' with the table, removing the duplicated rule 5 and the table's separate heading text.
- Renamed the table column to 'What the user sees' and kept the 'never let through on an error' sentence as a single lead-in.
- Reworded rule 3 and rule 4 slightly for plainer sentences. No behavior changed.

### Holes
- None.
