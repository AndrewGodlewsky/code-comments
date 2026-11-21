## Review of auth-01 (rewrite-v7, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- No questions were shown, so the rewrite is driven by the skill's layout and by the document itself.
- Added a Summary at the top: how the app works today, the main flow, and why Postgres.
- Added a Terms section defining CSPRNG, bcrypt, advisory lock, session fixation, __Host- prefix, SameSite=Lax, sliding window and fail closed.
- Moved the diagram up so the summary and terms precede it and the notes follow it.
- Cut the closing 'Checks against the requirements' list, which restated rules already given in the steps.
- Merged the scattered login bullets into numbered steps and removed duplicated statements (lockout not extending itself, same response for unknown/wrong, incoming ID never reused).
- Merged the Cookie reasoning into the Terms, and shortened the Decisions table rows that repeated step text.
- Turned the Storage failures bullets into one table; kept every rule, message, Retry-After and logging rule.
- Added an Open questions section (email length cap, advisory lock held through bcrypt); no other facts were dropped.

### Holes
- None.
