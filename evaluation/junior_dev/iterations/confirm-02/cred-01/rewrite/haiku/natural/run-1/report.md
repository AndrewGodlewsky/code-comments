## Review of cred-01 (rewrite, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Summary cut to three sentences and placed before the terms. It no longer repeats the steps.
- Added a Terms section defining the terms a newcomer would not know: Web/API server, Postgres, session cookie, token, CSPRNG, SHA-256 hash, CSRF token, Idempotency-Key, row lock and last-used buffer.
- Merged the state notes into one Where state lives section. Every field, size, interval and retention fact from the first version is kept.
- Kept the sequence diagram unchanged in content, placed between the state section and the flow notes, as the diagram form requires.
- Replaced the four long failure paragraphs and the repeated flow text with four numbered flow notes (trigger, rule, data) and one failure table. Each failure outcome now appears once, in the table.
- Moved the cross-flow rules (own tokens only, CSRF and no-store, the single 401 body, 90-day expiry with no renewal) into one list after the flows.
- Gave a one-clause reason for each failure outcome in the table, such as why 503 is not 401 and why the row lock is needed.
- Kept all three open decisions as open questions at the end, with the recommendations stated.
- Checked the first version line by line. No requirement, limit, status code, message text, header or retention rule was dropped. The Authorization header and create response redaction, the no-cache rule, and the 404 and 200 revoke behaviour are all kept.
- No junior questions or answers were supplied, so no answer-driven changes were made. The rewrite is based only on the first version and the brief.

### Holes
- None.
