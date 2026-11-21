## Review of cred-01 (rewrite, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a two-to-three sentence summary at the top that says how the system works today, what is added, and why it is shaped this way.
- Added a Terms section defining token, active token, session authentication, plaintext and orphaned token in one line each.
- Added a single 'Rules that apply across the flows' list holding every stated requirement (name length and uniqueness, limit of 10 and message, 90-day non-renewable expiry, show once with Copy button and no support/engineering recovery, SHA-256 only, own tokens only, no validity cache, database clock).
- Moved the schema into one short paragraph just before the diagram, with the meaning of 'active' stated once.
- Replaced the 'Decisions that shape the diagram' list with a shorter 'Notes on the diagram' placed after the diagram, each note giving its reason in a clause. Merged the repeated statements on revocation, last-used throttling, plaintext handling and ownership into one place each.
- Cut repeated wording between the decisions, the diagram notes, the state table and the failure list (for example the 1-write-per-hour and 1-hour-stale facts, and the orphaned-token explanation).
- Turned the failure bullet list into a table, and added the lost-revoke-response row so each flow's failures appear together.
- Put the limit message text and the name-clash hint into the diagram's 409 lines, so a reader sees them at the step they apply to.
- Removed the duplicated Token SHA-256 note from the state table and kept the entropy reasoning in the notes. Dropped the separate 'Token validity cache: none' explanation beyond the table row and the rules list.
- Kept both original open points unchanged. Nothing was added to the design.

### Holes
- None.
