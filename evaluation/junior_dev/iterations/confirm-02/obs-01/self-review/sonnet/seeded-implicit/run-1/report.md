## Review of obs-01 (self-review, author sonnet, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Rewrote the diagram so it actually shows the mechanism: evaluation insert with conflict, the unique-index duplicate suppression branch, the timer loop, the ack webhook and the resolution path. The original had one line per step and no branches.
- Dropped the separate timer queue. Timers are rows in an actions table in Postgres, so there is one place for state and one mechanism that both instances use.
- Explained how the two evaluators coordinate (unique keys, SKIP LOCKED, incident row lock) instead of just saying 'through Postgres'.
- Defined the tables (evaluations, incidents, actions, page_log) and what each stores, replacing the bare 'page_log table' bullet.
- Stated how the 5-minute clock works: fixed times set at incident open, so failures cannot delay it, and the on-call lookup happens at fire time to handle the 09:00 handover.
- Replaced the terse failure bullets with specific handling for push/SMS failure, schedule failure, metrics failure, worker crash, duplicate acks and resolve-before-ack, and noted the at-least-once tradeoff and the both-evaluators-down gap.
- Spelled out terms the original left implicit (consecutive breaches, the 500-request minimum, EM) and added a one-paragraph summary and component descriptions for a reader new to the stack.
- Added a short Terms paragraph defining rule, level, and action so a reader new to the project can follow the diagram and notes.
- Reordered the opening-an-incident step in the diagram so the check for an existing unresolved incident comes first, instead of showing an INSERT followed by a branch that undid it.
- Numbered the diagram's phases (1 to 5) to match the flow in the notes.
- Explained FOR UPDATE SKIP LOCKED in plain words and stated that the worker holds the transaction open while sending, which is what makes the crash recovery claim ('the claim lapses') understandable.
- Noted that an acknowledgement may briefly wait on an in-flight page because of the incident row lock.
- Clarified that the escalation worker also serves the acknowledge webhook, and that acknowledgement cancels pending page actions (not notices).
- Bolded the lead-in of each failure-handling bullet so failure cases are easy to scan, and tightened wording throughout.
- Added a short 'How it flows' paragraph so the reader gets the whole lifecycle before the details.
- Added definitions for evaluation, incident, page, and kept rule, level and action; moved terms before components.
- Clarified that each instance runs both an evaluator and a worker, and that the webhook can hit either instance; reworded the summary to say so and dropped the mixed 'evaluator instances' wording.
- Renamed diagram section labels from '1.-5.' to 'Phase 1-5' so they do not clash with autonumbered message numbers.
- Moved 'P->>E: page' before the page_log write in the diagram so it follows the send; made the ack and resolution steps show the incident row lock, matching the text.
- Explained the partial unique index in plain terms (the database refuses a second unresolved incident).
- Clarified that SKIP LOCKED locks the action row, and that page, ack and resolution all lock the incident row first (previously 'every action').
- Added a note that if the winning instance dies right after its insert, the next minute's evaluation recovers within a minute.
- Made the level 3 alert precise: 'last level failed' became 'level 3 page failed', with the reason (no next level).
- Reworded the 'cancels itself' sentence to say the claimed action waits for the incident lock before seeing the new state.
- Renamed 'Both evaluator instances down' to 'Both instances down' and 'How the two evaluator instances coordinate' to 'How the two instances coordinate' for consistency.

### Holes
- None.
