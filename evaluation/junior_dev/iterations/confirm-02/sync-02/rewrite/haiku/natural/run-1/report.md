## Review of sync-02 (rewrite, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a plain-language summary (what the sync is and how the first download and later updates fit together) and a 'How the system works today' section, because the plan changes an existing system.
- Added a Terms section defining only names a newcomer would not know: change feed, tombstone, generation, active and staging generation, swap, H0, since, after_id, keyset pagination, purge_floor, resync required and WAL mode. Everyday words such as transaction and row are not defined.
- Merged the 'Starts when' and 'Trigger' fields into one Trigger line per step, and gave every step the same order: trigger, action, why, data moved, state, failure.
- Stated the Wi-Fi gate, the 15-minute gate and the one-request-at-a-time rule once, in step 1. Step 10 now refers back to that gate instead of repeating it.
- Kept the retry policy once, under Shared rules, and referred to it from steps 3, 7 and 10 instead of restating it.
- Moved the seven verification scenarios out of the steps into a separate 'How to test it' section, so how the system runs is kept apart from how it is built and tested. All seven scenarios are kept as written.
- Kept every number, endpoint, limit, retry wait, storage estimate, server rule, local table, risk and open question from the first version. The four gap cases in step 7 and the failure cases in steps 4, 5 and 9 are kept.
- Reworded for short sentences and one idea each. Removed step codes and cross-references that pointed elsewhere; references now name the step number only.
- Holes left open, not invented: step 9 Case B says to mark generation N as needing replacement, but the local generation table has no field for that, and the first version does not name one. Also unclear: the first version limits the retry backoff timer to Wi-Fi during full downloads, so it does not say how backoff works for incremental sync on cellular.

### Holes
- None.
