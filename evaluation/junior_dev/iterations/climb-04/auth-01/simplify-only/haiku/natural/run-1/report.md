## Review of auth-01 (simplify-only, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Cut the 14-item Choices list. Each decision now appears once, in the summary, terms, notes or failure table, so nothing is said twice. No decision was dropped.
- Moved the Redis-versus-Postgres reasoning into one sentence in the summary, so the brief's request to justify the store is still answered.
- Merged the session validity rule into the expiry notes, and merged the rolling-window, fixed-lock and lock-not-extended rules into one lockout note.
- Merged the three storage-failure bullets and the status table into one failure table with one row per case. Login, protected-page and logout failures are each in that table.
- Put the terms before the diagram and the notes after it, as the diagram layout asks. Moved the cleanup job and CSRF details into the notes, next to the rules they belong to.
- Replaced the 'Known gaps' section with an open-questions section at the end, as the layout asks. Shortened the gap wording without changing it.
- Kept the Mermaid sequence diagram unchanged, so the flows still match the rules. Added one line saying the diagram omits the storage-error branches and the table covers them.
- Changed no behaviour: status codes, cookie attributes, timing, lock rules and the storage-failure responses are unchanged.

### Holes
- None.
