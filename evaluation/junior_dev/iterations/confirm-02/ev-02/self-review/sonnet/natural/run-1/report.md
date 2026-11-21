## Review of ev-02 (self-review, author sonnet, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a two-sentence opening that says what the service does, for readers new to the project.
- Removed the vague claim that a 6 h wait exceeds what the visibility timeout is meant for (the queue allows up to 12 h). The decision now rests on the 15 min delay cap and the unusable dead-letter topic.
- Defined lease, fan-out and fencing token where they first appear, and explained SKIP LOCKED in plain terms.
- Merged the 'claim time' and 'send time' subscription checks into one: the check at the start of every send. Made the state table, send steps and 410 section agree.
- Fixed the flowchart lease label from 'next_attempt_at + 60 s' to 'now + 60 s', matching the SQL.
- Fixed the wait list to say it applies after attempts 1 to 7.
- Explained why the janitor exists: the claim query skips rows with attempts >= 8, so a crash on the 8th attempt would otherwise strand the row.
- Noted that attempt numbers in delivery_attempts repeat across replay cycles and should be ordered by started_at.
- Clarified that the service may only disable subscriptions, not re-enable them.
- Promoted the bold-labelled steps to headings, split replay and 409 conditions into sub-bullets, and tightened wording throughout. The format and decisions are unchanged.
- Added an Overview and a short glossary (delivery, fan-out, dead-letter, lease) up front so a reader new to the project has the terms before they appear.
- Moved the lease explanation into a bulleted list under the state table and added that a retry wait replaces the lease time in next_attempt_at.
- Turned dense paragraphs (ingest failures, claim explanation, 410 handling) into short bullet lists.
- Corrected the core-DB-outage row: the claim uses only the service DB, so the outage hits at send time. Added the matching core-DB-error branch to the flowchart, which was missing.
- Fixed the signature header to read t=<t>,v1=<hex> instead of t=..,v1=..
- Clarified the fencing explanation (a reclaimed row makes the stale worker's write match nothing).
- Clarified the replay-409 reasoning and rephrased the 7-day retention note as a design choice rather than 'my choice'.
- Kept all design decisions, SQL, tables, section order and the flowchart structure unchanged.
- Defined core DB and service DB in the terms list, so later uses are unambiguous.
- Replaced the 'fencing token' jargon with a plain explanation: the attempts value from claim time, which a reclaim raises, so a stale worker's write matches nothing.
- Clarified in the claim section that attempts counts the attempt now starting.
- Reworded the waits ('after attempts 1 to 7') and the core DB write note so the exact columns written are stated.
- Made replay precise: it checks the core DB first, returns 404 for a missing delivery and 409 for a non-dead one, replacing the vague '404 or 409'.
- Trimmed small redundancies in the state table; the flowchart and all design decisions are unchanged.

### Holes
- None.
