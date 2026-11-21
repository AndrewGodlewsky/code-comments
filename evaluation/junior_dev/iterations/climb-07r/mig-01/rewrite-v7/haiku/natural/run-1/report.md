## Review of mig-01 (rewrite-v7, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Restructured the document into the required order: a summary, a terms list, a How the system runs section (rules and where state lives), the rollout checklist, and open questions. Rollout content is kept separate from how the system runs.
- Defined every term a newcomer would not know in one plain line, including outbox, tombstone, copy rule, lease, compare pass, mirror, id counter, circuit breaker and retryable 503.
- Moved the copy rule, deletes, repair-reads-primary, ids, backfill progress and repair retry/alert rules into one place each (Rules). Steps now refer to them by name instead of repeating them. The repair retry and alert text appears only in Rules.
- Gave every step the same four labelled parts: Starts, What it does, Where state lives, If it fails. Replaced references such as 'Do step 4.1' with the actual steps, so each step stands alone.
- Changed the Phase 6 (rollback) abort. The first version pointed rollback failures to 4.5, which sets the flag to mysql. During a rollback that would make MySQL authoritative while Postgres still holds unmirrored writes, risking divergence. Rollback aborts now set users_write_state back to postgres, as 6.3 already said.
- Added a 'Starts' line to 8.2 and 8.3, which the first version left out. Added 6.4's abort path (id mismatch aborts as in 6.3), which was missing.
- Clarified in 5.1 how a delete is mirrored to MySQL (the row is removed and the tombstone is written on that side). The first version named the tombstone write in Postgres but did not say what the inline copy to MySQL does for a delete.
- Added the current-system facts from the existing files (row count, peak load, erasure rate, primary and replica names, and the existing empty pg-core pool) to the summary, so a newcomer can see the scale. Kept every number from the first version and the brief.
- Added two open questions the document could not settle: the brief's no-reappearance rule has a window where a copy that read the user before erasure can land in Postgres before the delete is repaired; and the Postgres side of the per-user lock is not named.

### Holes
- None.
