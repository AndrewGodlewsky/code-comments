## Review of sync-01 (rewrite, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Cut the first version's four short bullets. Their facts now sit in the terms, steps and failure table, and the 'sent changes are not edited' rule now sits in step 1.
- Restored facts the first version dropped: the three sync triggers and the 60-second interval, the upload-then-download order, the full-body rule, the collapse rule that keeps the original base version, the version and change-log sequence numbers, the processed change IDs, the conflict copy title with ' (conflict)', every device picking up the copy on its next download, the batch limits of 100 changes and 500 log entries, the cursor, the out-of-scope list, and the local-only starting point.
- Added a terms section that defines version, base version, outbox, change ID, change log, processed change IDs, cursor and conflict copy.
- Rewrote the diagram so each phone's queued change carries a name and base version. It now shows the server's version check and the conflict copy being logged, and Phone B's download picks up the copy. The first diagram had none of these, so a reader could not tell where the losing text went.
- Added numbered steps with trigger, action, where data lives and failure handling, plus a failure table. Added the decisions this needs and marked them in the text: a conflict removes the change from the outbox, a download applies entries in one local write with the cursor, and a log entry carries the full body.
- Added two open questions: the base version of an edit made while an earlier change is still in flight, and whether log entries carry full bodies. The brief does not settle either, so I did not guess.

### Holes
- None.
