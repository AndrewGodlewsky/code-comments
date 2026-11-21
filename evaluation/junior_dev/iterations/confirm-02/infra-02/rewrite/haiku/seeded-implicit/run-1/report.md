## Review of infra-02 (rewrite, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Kept the first version's diagram form, placed the summary and terms before it and the notes after it.
- Added a summary of what the pipeline does and why it calls deploy.sh instead of replacing it.
- Added a terms section defining deploy.sh, SSM tags, stable, canary, migrations, named locks, manual approval, the deployment window, Prometheus and kubectl rollout undo.
- Rebuilt the Mermaid flowchart so each node names its trigger, what it reads or writes, and its failure path (added PR node, staging rollback, canary-off, production failure path, expiry).
- Added notes per step covering trigger, data and failure, including the 1% canary threshold, the 15-minute watch, the 72-hour clock, and the window and lock rules.
- Added a single failure table covering each step.
- Decided and documented how overlapping runs behave: superseding, a production lock, and waiting for the window.
- Decided and documented that a missing canary reading counts as a failure, and that a rejected approval ends the run without an announcement.
- Kept every stated fact from the brief and the first version: PR checks unchanged, one image tagged with the SHA, parallel tests with the retry rule, staging and production via deploy.sh, release-approvers and the author rule, 72 h expiry, window, canary 1% threshold, rollout undo, staging and production locks, superseding, and #deploys announcements.
- Listed four open questions in the document instead of guessing: rollout undo versus SSM state, announcing superseded runs, a limit on waiting approvals, and the canary check interval.
- No junior questions or answers were shown, so no answers were applied and no changes came from them.

### Holes
- None.
