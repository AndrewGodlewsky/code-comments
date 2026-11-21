## Review of sync-01 (rewrite, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a short summary up front that says how the app works today (local-only SQLite, no server) and the main flow in three sentences.
- Added a Terms section defining version, base version, change log, cursor, outbox, change_id, applied-changes table, conflict and sync, each in one line.
- Replaced the scattered 'Rules that make it safe' and 'Where state lives' prose with a numbered Steps section in time order (edit, trigger, upload, judge, ack, download). Each step has its trigger, action, data location and failure handling.
- Merged the Collapse, Batching, Conflict check, Ordering and Phone-after-conflict-ack rules into the steps they belong to, so each rule appears once.
- Merged the download-time rows from the failure table (own writes in the log, queued change on a downloaded note) into step 6, and kept the table for the failures that cross steps, with pointers to steps for the rest.
- Moved the Assumptions into Where state lives and step 6 (title is part of the content, entries carry full snapshots) rather than a separate section.
- Added the server's check of change_id before the version compare in step 4, to make the retry path explicit.
- Kept the diagram unchanged. Kept every number and rule from the first version (100 per batch, 500 per page, 60 s, triggers, ' (conflict)' title, full bodies, collapse keeps original base, never discard the loser, out of scope list).
- Cut the duplicate statements of retry, cursor advance and one-sync-at-a-time that appeared in both the rules and the table.
- Open questions section now says None, since no unknowns were raised.

### Holes
- None.
