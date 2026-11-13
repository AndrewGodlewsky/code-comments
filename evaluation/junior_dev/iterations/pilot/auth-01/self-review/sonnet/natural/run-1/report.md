## Review of auth-01 (self-review, author sonnet, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short Summary section so the whole approach is clear before the details.
- Explained jargon inline: what the advisory lock is and how long it is held, and what the sweeper's lock does.
- Clarified the lock-expiry reasoning (failures are older than the 10-minute window once the 15-minute lock ends).
- Stated that email is trimmed as well as lowercased consistently, including in the stored tables and the requirement check table.
- Clarified that the indexes serve the cleanup job.
- Reworded the logout rationale and the failure-behavior heading for plainer reading.
- Made requirement 3 in the check table more explicit about the mechanism.
- Rewrote the summary to say plainly what the cookie and the server record each hold
- Gave the sessions table full column syntax (PRIMARY KEY, REFERENCES) instead of arrow shorthand
- Stated that 'email' in the throttle tables is the text the user typed, and why that matters
- Converted the sweeper's deletions into a short list and said what the advisory lock does in plain terms
- Added 'a request rejected as expired' to clarify when lazy cleanup happens
- Clarified that Redis could be adopted later behind the same interface
- Introduced the brute-force rules with a lead-in line and tightened the lock-expiry sentence
- Reworded the 503 login explanation to say credentials were never judged
- Diagram step now says 'trim and lowercase email' to match the rules and requirement 1
- Minor wording tightening throughout; intent, format and all decisions unchanged
- Light edits only: the document was already clear and complete, so structure, format, and content are kept.
- Summary: changed 'Brute-force counters are kept in Postgres too' to 'are also kept in Postgres' for smoother reading.
- Expiry section: reworded 'The three cases are handled identically on purpose' to 'All three cases are handled the same way, on purpose.'
- Sweeper bullet: 'so it runs once per cycle' became 'so the job runs once per cycle', to make clear what 'it' refers to.

### Holes
- None.
