## Review of dp-02 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Added a Terms section that defines event, batch, received_at, duplicate, raw log, archive, KV store and partition, so a reader new to the project and stack can follow the plan.
- Grouped the six steps into a Live path and a Replay path, and kept the numbered step-by-step format.
- Stated the partition rule plainly: an event belongs to the UTC day of its server-side received_at, never its client timestamp.
- Made the collector step explicit: malformed events are rejected individually, clients never retry rejected events, and 202 is returned only after a durable write.
- Explained the 7-day retry window and what it requires: the KV dedup key must have a TTL of at least 7 days, and the write must be atomic (set only if absent).
- Added a replay step that reads the 7 days before the chosen day, so that first copies are found and a duplicate that arrived after its first copy is excluded from the day it was replayed into. This follows from the first-copy-wins rule and the 7-day retry window, but the original brief did not spell it out; it is a derived detail to confirm.
- Explained why replay reads the archive instead of the raw log (the log keeps only 14 days) and why it never touches the KV store, so live ingestion and dedup state are unaffected.
- Explained the 02:00 UTC close as a gap that lets live processing finish the previous day first, and described the staging table and atomic partition swap so dashboards never see a half-rebuilt day.
- Expanded monitoring to name consumer lag as tied to the 5-minute target.
- Moved bot filtering into an Open decision section, stating that it is undecided and noting which steps it would affect, without choosing an option.
- Added a short 'How the pieces fit' section showing the live flow and noting that replay reads only the archive.
- Defined terms the reader may not know: UUID, UTC, replicated, append-only, object storage, KV store, TTL, atomic, closed day, staging table, geo-IP, user-agent, reject bucket.
- Added a 'Closed day' term and a 'Staging table' term, since both are used in the steps but were not defined.
- Explained what 202, 429 and 5xx mean, and what 'durably stored' means, in plain terms.
- Step 2 of replay: stated the exact window (days D-7 through D-1) instead of 'the 7 days before D'.
- Step 3 of replay: made explicit that the rule drops copies on day D whose first copy arrived on an earlier day.
- Live step 4: explained that the KV check-and-write is atomic so two simultaneous copies cannot both pass.
- Stated that the raw log is not read by replay in the replay section's closing note, and kept the original reasoning.
- Kept the original numbering, the 5-minute target, the 02:00 UTC close, the 14-day and 90-day retention, and the open bot-traffic decision unchanged. The brief does not say how to order two copies whose received_at is identical; the document keeps the original 'first copy we receive' wording, and this ordering should be confirmed before implementation.
- Added a one-line flow explanation and a short note that the archiver and replay sit beside the live flow, so the reader sees the two paths before the details.
- Expanded the terms list with plain-language definitions for 'key-value store', 'atomic', and 'consumer lag', and added the 'Atomic' term, since later steps depend on it.
- Defined 'raw log' retention (14 days) and 'duplicate' handling in the terms, so a reader sees what each term means before the steps use it.
- Replaced 'Replicated means it is copied to several machines' wording with 'copies are kept on several machines' and stated the data-loss consequence directly.
- In the live processor, grouped the three actions under labelled bullets (duplicate check, enrich, write) and stated that the check and write are one atomic step, which the original implied but did not name as a single step.
- In replay step 3, defined 'first copy' explicitly as the copy with the earliest received_at, so the rule is testable without reading the rest of the plan.
- Added a closing sentence to replay explaining why it cannot affect live deduplication or live ingestion, as a consequence of its reads and writes.
- Kept the bot-traffic decision as open, and stated its effect on steps 4 and 5 more explicitly. No decision was made.

### Holes
- None.
