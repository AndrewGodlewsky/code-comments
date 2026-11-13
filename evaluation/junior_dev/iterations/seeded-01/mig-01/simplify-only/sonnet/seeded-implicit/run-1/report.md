## Review of mig-01 (simplify-only, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Rewrote the terse checklist into the newcomer layout: summary and how it works today, terms, runtime behaviour, rollout steps, failure table, open questions
- Separated how the system runs (write, repair, erase, read) from how it is rolled out (nine steps)
- Merged dual-write, repair and backfill rules into one 'copy' term with the single version rule
- Replaced separate mechanisms with one: a pending row and a sweeper, with no job queue
- Gave every rollout step the same four parts: start, action, state, failure
- Merged the 'keep MySQL in sync' note and rollback into one step, and defined the 90-second switch as numbered sub-steps
- Removed codes and cross-references; folded the failure cases into one table
- Flagged tombstone retention and backup method as open questions
- Left a wording slip in step 7's failure line (it says mysql_primary's mode) that should be read as set write_mode back to dual_mysql_primary

### Holes
- None.
