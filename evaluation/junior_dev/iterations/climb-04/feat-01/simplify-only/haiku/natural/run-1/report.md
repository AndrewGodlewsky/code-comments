## Review of feat-01 (simplify-only, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Merged the 13 original steps into 8 runtime steps (click, sync CSV, large-export row and enqueue, job attempt, final failure, emails, status and download endpoints, page) plus a separate build-and-rollout section, so how the system runs is kept apart from how it is built and released.
- Moved the rollout items (query refactor, table migration, measurement gate, two-stage release) and the test list into 'Build and rollout', out of the runtime flow.
- Replaced the separate 'Decisions this plan makes' section: status values moved into Terms, and the payload-only enqueue and replica-only reads moved into the steps they govern.
- Folded the two stale guards (queued after 10 minutes, running after 2 hours) into a single 'Stale checks' list under the click step, with the 96-minute retry-window reasoning kept in one sentence.
- Removed the step-number and cross-reference clutter (for example 'go to step h only', 'the retry takes the step a path') and wrote each branch so it stands alone.
- Consolidated the failure statements that repeated across the job attempt and final-failure steps; each failure now appears once, at the step where it happens.
- Shortened the terms to one line each, and cut the duplicated explanation of the replica and primary split, which is stated once in Terms.
- Kept every threshold and decision unchanged: 10,000 rows, 500-row and 5,000-row read pages, 8 MB parts, 900 s and 256 MB gate, 24-hour links, 7-day expiry, 404 for other users, 410 for expired objects, and all seven open questions (reworded only for length).

### Holes
- None.
