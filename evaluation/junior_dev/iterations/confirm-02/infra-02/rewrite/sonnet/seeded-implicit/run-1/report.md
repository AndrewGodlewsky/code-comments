## Review of infra-02 (rewrite, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Replaced the bare node list with a diagram that shows each step's trigger, what it writes and its failure path, including the failure sink, the superseded exit, the window loop and the author check.
- Added a summary that says how deploys work today and how the new flow goes from merge to production.
- Added a terms section: tag, deploy.sh modes, stable and canary, SSM tags, migration, lock, approval job, superseded and deployment window.
- Added the production window rules as stated in environments.md: start Monday to Thursday, 09:00 to 15:00 UTC, and a started deploy may finish later.
- Dropped 'Rollout failures use kubectl rollout undo'. It bypasses deploy.sh and the SSM tags, which the brief says to keep. Failure handling is now: staging smoke failure uses deploy.sh rollback staging, and a failed staging or production deploy does not call rollback. This is because deploy.sh writes the tags only after success, so rollback would go back two versions.
- Merged 'Staging and production locks' into steps 3 and 5 with exact hold points: the staging lock covers the deploy plus smoke tests, and the production lock runs from after approval to canary-off.
- Merged 'Older runs get superseded' into rule 1: a run is superseded when a newer run exists and it has not yet taken the production lock, checked at the gates.
- Added decided details for how the canary is measured: the Prometheus query, a sample every 30 seconds for 15 minutes, a 1% threshold, and no data counts as a failure.
- Added the author-exclusion rule for approval and the 72-hour expiry announcement.
- Added a window loop: after getting the lock, if outside the window, release the lock and wait for the next window.
- Added the migration fact: canary runs the migration, the production step then does nothing, and nothing undoes a migration.
- Added a short rollout section, and open questions about author exclusion, low-traffic canary noise and a newer run failing after the older one was superseded.

### Holes
- None.
