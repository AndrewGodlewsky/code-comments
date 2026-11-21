## Review of auth-03 (simplify-only, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a short summary before the diagram: how the existing system works today, then the new flow in plain words.
- Added a terms list (reset token, reset_tokens, session, generic message), each defined in one line.
- Kept the diagram unchanged, with the summary and terms before it and the step notes after it.
- Replaced the Notes list and the repeated flow lines with three numbered steps. Each step now states what starts it, what it does, which data it keeps, and what happens when it goes wrong. Each rule sits in the step it belongs to, so nothing is said twice.
- Moved all failure cases into one table.
- Cut the repeated arrow-chain flow lines, since the numbered steps say the same thing.
- Made a design decision the brief left open, recorded in the file: the rate limit counts this account's reset_tokens rows from the last hour, and old rows are marked used rather than deleted.
- Made a design decision the brief left open, recorded in the file: issuing a link and saving a new password each run in one database transaction, and a database error changes nothing.
- Made a design decision the brief left open, recorded in the file: logging out every device means deleting the account's sessions rows.
- Added two open questions the brief leaves unanswered: what happens when the reset email is dropped after the link is saved, and where the breached-password list comes from. No answers were invented.

### Holes
- None.
