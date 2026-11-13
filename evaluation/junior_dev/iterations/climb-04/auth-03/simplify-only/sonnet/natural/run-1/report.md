## Review of auth-03 (simplify-only, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added the newcomer layout at the top: a short summary with how mail and sessions work today, then a terms block defining reset link, token hash, password_resets, live link, and the existing tables.
- Removed the standalone Tables block and the reset_email_log remark, now covered by the terms block.
- Replaced the ASCII failure-paths section C with a table of step, what goes wrong, and what happens.
- Cut the 'same latency' wording from the diagram, and merged the Enumeration note into one sentence under the request diagram.
- Cut the Storage note, the No auto-login note and the Expiry and single use duplication. Merged them into the Single use, Reset and logout, and Rate limit notes.
- Moved the silent email failure gap into Open questions at the end, and shortened it. Dropped the separate note on the same topic.
- Dropped the 'link remains usable' repetition and other per-row repeats of the same rule.
- Left the two diagrams unchanged in form, since the brief asks for ASCII.

### Holes
- None.
