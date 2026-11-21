## Review of mig-01 (rewrite-v5, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered into the skill layout: summary (with how it works today), terms, how the system runs, rollout checklist, failure table, open questions.
- Removed the numbered 'Design decisions' section and its cross-references; each mechanism is now explained once under 'How the system runs' and in the terms.
- Added a Terms section defining SoT, version rule, outbox, sync worker, tombstone, fence, the two flags, backfill and comparison, including why the job queue was not used.
- Merged the repeated outbox, copy-statement and fence descriptions from decisions 1-4 and steps 4 and 11 into single descriptions of write, repair, copy, delete and read behavior.
- Separated runtime behavior (write path, repair, deletes, reads, ids) from the rollout steps.
- Added a one-table failure summary.
- Added a short 'Why the fence' line explaining the fence stops stale instances from splitting the brain.
- Cut detail not needed for the main flow: the circuit breaker is kept but shortened, sibling-module lint allowlist option shortened, 'my choice' wording neutralized, and the unique-email conflict handling kept in step 6 only.
- Added an open question about the unset backfill throttle interval; kept the rollback-while-Postgres-down limit as an open item.
- Kept all 14 rollout steps with their trigger, change, state and failure handling, and all numeric limits (2,000 batch, 5 s lag, 90 s pause, 40 s abort, 3 days, 14 days).

### Holes
- None.
