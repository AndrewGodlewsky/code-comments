## Review of mig-01 (rewrite-v7, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- No junior questions or answers were supplied, so the rewrite is built from the first version, the brief and the existing files.
- Added a Terms section defining source of truth, write mode, version, copy, pending table, tombstone, named lock, sweeper, comparer, scheduled worker and replica lag.
- Added a Write modes section listing mysql_only, dual, frozen, pg_primary and pg_only, which the first version used without defining.
- Added the decisions the brief left to us, each in one place: repair (sweeper driven by a pending table kept in the source of truth), switch coordination (frozen mode, wait for every instance, drain, then flip), backfill progress (saved in MySQL after each copied batch) and id assignment (Postgres sequence reset to max id plus 1 at the switch).
- Added the copy rule once, stating the version rule and the tombstone check, and referred to it from writes, backfill, sweeper and comparer.
- Added the tombstone and erasure flow, so the requirement that erased users never reappear is met.
- Added the 90-second pause limit as a worst-case calculation (85 seconds) in step 8 and the rollback path in step 9.
- Added the 2,000-row batch size, 5-second lag pause, 50-second run limit, and resume-after-crash rule to backfill.
- Added the reads fallback rule so reads never fail, and the 14-day and 3-day gates with their starting conditions.
- Added a failure table covering each main failure case, replacing per-step failure notes that repeated each other.
- Cut the first version's bare checklist wording and merged the steps so each one says what starts it, what it changes, where its state lives and what happens on failure.
- Kept every fixed requirement from the brief: dual writes, version rule, deletes, backfill conditions, reads and writes gates, availability, rollback window, and MySQL drop timing.
- Moved the unanswered questions (scheduler, read-source metric, stale reads, lock support, metric shape, alerting, email conflicts) into Open questions instead of guessing.

### Holes
- None.
