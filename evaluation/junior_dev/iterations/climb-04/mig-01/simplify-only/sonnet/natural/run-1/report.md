## Review of mig-01 (simplify-only, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered the file for a newcomer: summary of today's system and the main flow, then terms, then how the system runs, then numbered rollout steps, then open questions.
- Split 'how the system runs' (write path, deletes, reads, switch fence, state, ids) from 'rollout steps' so runtime design and rollout are separate.
- Replaced the scattered Design decisions bullets with a short Terms section, one line per term, including a single definition of the apply rule.
- Merged the repeated apply-rule mentions (dual write, backfill, repair, reverse sync, comparison) into one term.
- Turned the outbox and drainer description into numbered write-path steps with an explicit 'start, fence, commit, mirror, repair, alerts' order.
- Merged the three-part delete description and its tombstone/backfill remarks into one short Deletes section.
- Cut detail that does not affect the main flow: the 'Expected pause' repetition, the 'Measure' wording in step 0, and the 'Done when' duplication of step 2's check lists.
- Rewrote rollout steps as same-shaped entries (starts when, what it does, state, if it fails) and removed cross-references such as 'as described above'.
- Replaced the empty Open questions with a note that the pause estimate and quiet period are to be confirmed in rehearsal.

### Holes
- None.
