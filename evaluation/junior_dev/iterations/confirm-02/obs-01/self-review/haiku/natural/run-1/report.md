## Review of obs-01 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short opening paragraph that says what the design covers and states the core idea (one transaction per tick, with pages and timers committed alongside the state change) before the details.
- Added a Terms section defining tick, incident, page, outbox, idempotency key, row lock, and SKIP LOCKED, so a reader new to the project can follow the rest.
- Expanded the state table descriptions: what level, breach_events, pages and timers hold, and what the partial unique index enforces.
- Explained that breach events are logged for context and never page anyone.
- Clarified that the responder is looked up at send time, which is why the 09:00 handover is respected.
- Clarified that the duplicate-tick check relies on last_tick being equal to the tick time after the lock is granted.
- Stated that dispatched rows are claimed by one dispatcher, and that a double dispatch still yields one page through the idempotency key.
- Rewrote failure-handling bullets in plain sentences, and said a replayed webhook is ignored once its event ID has been processed.
- Added that a failed metrics query means the same tick is retried in the next minute.
- Clarified in the Assumptions section that a zero-request window has no defined rate, and that the resolve rule applies to any defined rate below 1%.
- Diagram: kept the same participants, flow and branches; shortened some labels (for example dropped the word 'table' and 'claim' wording) and replaced the percent sign in the note with the word percent-free text unchanged where it was already valid. No behaviour was changed.
- Added a short "core idea" section that explains the transaction, outbox and why messages are never sent inside a transaction, in plain words before the details.
- Expanded the terms list with plain-language definitions of partial unique index, ack webhook and heartbeat alert, and tightened the existing definitions.
- Clarified that the `pages` target is filled in at send time, not when the incident opens, and replaced the jargon phrase "resolved target".
- Added the `processed_events` table. The failure section already relied on it for replayed webhooks, but no table in the state list stored those event IDs.
- Defined `expected_level` as the incident level when the timer is created, and spelled out the level 1, then 2, then 3 escalation chain, including that no timer follows the level 3 page.
- Renamed the diagram participant from "Work queue" to "Dispatcher on each instance" so the sender role is clear. The diagram's logic is unchanged.
- Added a one-line reading guide above the sequence diagram.
- Added an assumption that a window which is neither a breach nor a clear window resets both streaks, since the brief's "consecutive" wording implies this but the document did not state it.
- Added a "short version" section at the top that states the design in plain terms before the details.
- Added a "Plain-language terms" section that defines error rate, trailing window, breach, clear, streak, incident, page, level, and the database and messaging terms, so a reader new to the stack can follow the rest.
- Rewrote the "How the 5-minute timers work" section as a numbered sequence of steps, with the three timer checks listed separately.
- Retitled the coordination section to "How the two evaluators avoid duplicates" and reworded it to say what each guard prevents.
- Turned the failure-handling bullets into a "What happens when something fails" list that names each failure first and then its outcome.
- Shortened wording in the state and assumptions sections and removed repeated explanations, without changing any rule, table, or threshold.
- Left the Mermaid sequence diagram unchanged, because its steps match the rules and it is already the required format.

### Holes
- None.
