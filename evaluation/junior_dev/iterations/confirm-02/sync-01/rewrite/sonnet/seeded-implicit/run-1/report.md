## Review of sync-01 (rewrite, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Rewrote the thin outline into the required order: summary, terms, rules and limits, diagram, numbered steps, failure table, build order, open questions.
- Added: a terms list defining outbox, change, base version, note version, change log, cursor, processed changes and conflict.
- Added: a full diagram with notes for the scenario (both phones offline, A syncs first, B conflicts), including a lost reply and an idempotent retry.
- Added: numbered steps that give each step its trigger, what it does, where data lives and how it fails. They cover edit collapsing, the case where a change is already in flight, the server transaction, reply handling, and pull paging with the cursor.
- Merged: the four vague bullets (conflicts, retries, cursor, batching) into the steps and the failure table, which now states the actual rules.
- Kept every fixed requirement: 100-change batches, 500-entry pages, 60-second and other triggers, upload before download, full bodies with no diffs, original base version on collapse, integer versions, change log, first write wins, conflict copy titled with the original title plus ' (conflict)', and out-of-scope items.
- Decided and stated: a change already sent is never edited, and a later edit waits as a separate change. Retries happen on the normal triggers with no backoff. Pull does not overwrite a note that has a queued change. One sync runs at a time per phone.
- Added: a short build-order section, separate from how the system runs.
- Added: two open questions (retention of processed changes and log, and duplicate creation of the same pre-existing note on two phones).

### Holes
- None.
