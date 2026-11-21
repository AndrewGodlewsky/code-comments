## Review of infra-01 (rewrite, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Kept every fixed requirement from the brief: additive-only migrations, stop on migration failure, 3 healthz passes at 10-second intervals, smoke tests, 10-minute abort without touching the listener, one-step switch, 15-minute watch with the 1% over any 5-minute window rule, no migration reversal, 30-minute old-colour window, and rollback as a normal deploy after shutdown.
- Added a summary (with how the system works today), a terms list, and a short rules section so the rules that apply to every step are stated once.
- Merged the first version's 'Build image' and 'migration lint' items into step 1, and merged 'Get the deploy lock' and 'Work out live / idle colour' into steps 2 and 3.
- Merged 'Health checks' and 'Smoke tests' into one gate step (6), since both must pass before the switch.
- Merged 'Release the lock' into the end of the paths that finish a run (steps 6, 9 and 11) and into the rules, instead of a separate final step.
- Split the first version's 'Keep old colour up' item into the hold (step 10) and the teardown (step 11) so the 30-minute wait and the shutdown rule are each stated once.
- Decided where deploy state lives: one record per service in the cloud parameter store, with the listener as the source of truth for the live colour.
- Decided the lock semantics: the lock is held for the whole 30-minute window, and a manual rollback job does not take it.
- Decided the failure handling the brief left open: abort shuts down the new colour; an automatic rollback shuts down the failed colour; a failed teardown is retried and then paged, with the lock kept.
- Added a failure table, and listed five open questions that the brief does not settle (metrics source, migration tool progress recording, the test listener, who clears a stuck lock, and the state record key name).
- The document is longer than the first version. This is because the brief's requirements cannot be dropped and the first version left out the timing, rollback and state details.

### Holes
- None.
