## Review of cred-01 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Replaced the bare diagram with a document that explains the terms first, then the diagram.
- Added the 'where state lives' section, which the brief asked for.
- Expanded each flow with the rules from the brief: the 10-token limit, the 90-day expiry, hashed storage, the once-per-hour last-used update, and no caching of validity.
- Added the failure cases, including the limit, bad token, and create response that never reaches the browser.
- Replaced the vague 'usual 4xx codes' with a specific rule for each error. The brief does not fix the exact status codes, so the 4xx choices are placeholders for the team to confirm.
- Added plain-language definitions for hash, SHA-256, expiry, session cookie and bearer header, so a reader new to the stack can follow the document.
- Replaced "a fixed scrambled value" with an explanation of one-way hashing and why a leaked database is safe.
- Added the rule that expiry cannot be renewed, which the brief requires but the draft omitted.
- Corrected the limit and duplicate-name checks: a transaction alone does not stop two simultaneous creates under Postgres's default isolation, so the draft now locks the user's row first. The diagram and the failure section reflect this. Please check the locking approach against the implementation.
- Added the lost-create-response case to the diagram as a note, since the brief requires it to be shown and the draft only described it in the text.
- Added roll-back steps on the refused create branches, so the transaction end state is visible.
- Split the bad-token case so that a missing header is listed with unknown, revoked and expired tokens, as the brief requires.
- Separated the Where state lives and Flows sections under clear headings and shortened the diagram labels, keeping the same four flows and the same overall structure.
- Added a Rules section that lists the name length, the 10-token limit, the one-time display and the ownership rule in one place, so the reader does not need to find them in the flows.
- Expanded the Hash term to explain what SHA-256 is and why a leaked database is not enough to use tokens.
- Defined Row lock and explained what it does, since the create flow depends on it.
- Explained what Bearer header, Postgres and the API client are for a reader who does not know the stack.
- Explained that the server does not cache validity, so a revoke applies at once, and that last-used is written at most about once an hour per token.
- Replaced a semicolon-joined phrase in the list note and clarified the limit failure: without the lock, two creates could both read 9 and insert, going over the limit.
- Added a diagram note that a missing or malformed Authorization header gets the same 401, since the original diagram only covered unknown, revoked and expired tokens.
- Made the create-failure and bad-token wording consistent with the diagram (4xx for limit and duplicate name, same 401 body for all bad tokens) and noted that a revoke of another user's token returns the same 404 as an unknown token.
- Kept the brief's structure: one Mermaid sequenceDiagram with notes, covering create, list, API call and revoke, plus the failure cases.

### Holes
- None.
