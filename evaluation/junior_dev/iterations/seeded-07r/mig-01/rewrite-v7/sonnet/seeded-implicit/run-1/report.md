## Review of mig-01 (rewrite-v7, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered into summary, terms, how it runs, rollout checklist, failure table, open questions, so runtime behavior is separate from rollout.
- Added definitions for tombstone, pending list, sweeper, comparer, version rule, write_mode values and flag refresh.
- Decided the repair mechanism: pending list written in the same transaction as the change, drained by a database-polling sweeper rather than the Redis job queue, because Redis can fail and dead-letters are not processed.
- Decided deletes: tombstones in both databases, checked by every copy, never removed.
- Decided backfill progress: one-row table in Postgres updated in the same transaction as each batch.
- Decided switch coordination: paused mode, wait for all instances via app_flag_value, drain pending, set sequence to max id + 1, flip, with a 45-second abort deadline to stay under 90 seconds; rollback uses the same procedure.
- Decided new ids: Postgres sequence set during the pause, MySQL keeps accepting explicit ids for rollback.
- Added the Postgres read fallback to MySQL and the comparer's skip rules and auto-repair.
- Restored requirements the first version dropped or abbreviated: 2,000-row batches in primary-key order, 5-second lag threshold, resume after crash, 503 retry, 90-second pause limit, 3-day and 14-day periods, backup before drop, zero mismatches before reads.
- Added per-step trigger, state and failure to every checklist item, and a failure table.
- Cut nothing of substance; the document is longer than 1.5x the original because the original left the four design decisions undefined.

### Holes
- None.
