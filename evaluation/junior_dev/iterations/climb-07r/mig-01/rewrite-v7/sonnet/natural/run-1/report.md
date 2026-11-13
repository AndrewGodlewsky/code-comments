## Review of mig-01 (rewrite-v7, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered into the required layout: summary, terms, how the system runs, rollout checklist, failure table, open questions. Separated run-time mechanics from rollout steps.
- Merged the Design decisions and State locations material into 'Terms' and 'How the system runs'. Added a Terms list (source/follower, outbox, relay, tombstone, fence, reconciler, flags, backfill) with one-line plain definitions.
- Merged the outbox, inline copy, relay, copy function and fence bullets into a numbered write path plus one copy-function section. Stated the Redis rationale once.
- Moved the read fallback, read-lag and StaleWrite explanation out of the ramp step into a single 'Reads' paragraph.
- Moved column-type and non-unique email index reasoning into one paragraph, removing the duplicate in the unique-index step.
- Added an opening sentence on how users are read and written today.
- Removed cross-references like 'see step 8' and 'step 5's condition' where a plain phrase would do. Kept step numbers only where they name a gate or a rollback.
- Tightened wording in step 11 and step 12 failure notes. No facts, numbers or limits were dropped: all thresholds, timings, flags and gates were kept.
- Added two open questions: the final-dump policy and the lack of a tombstone retention rule. These were already implied in the original but not listed.
- No junior questions were supplied, so nothing was added beyond the defined terms and the opening sentence.

### Holes
- None.
