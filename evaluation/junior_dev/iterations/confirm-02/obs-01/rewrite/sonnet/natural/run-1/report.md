## Review of obs-01 (rewrite, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered: summary (with how today's cron-and-inbox system works), terms, fixed rules, diagram, then notes, as the skill asks for diagrams
- Added a Terms section defining the existing services, streak, level, lease, SKIP LOCKED, unique partial index, idempotency key, watchdog and the evaluator, dispatcher and sender roles
- Added a Fixed rules list so every number and rule from the brief is stated once in one place (2%, 500 requests, 3 breaches, 1%, 10 minutes, 5-minute levels, push then SMS)
- Added a note to the diagram that section numbers match the notes, and that resolution happens inside the evaluator's transaction
- Turned the failure bullets into one table (what fails / what happens), same content
- Merged the original duplicated explanations of clock advance and timeline into the timers section
- Added an Open questions section: provider idempotency support, and unfixed values for lag, polling interval, backoff and watchdog threshold
- Left the diagram's flow unchanged
- Cut nothing stated in the first version

### Holes
- None.
