## Review of infra-01 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Added a Terms section that defines colour, target group, public listener, test listener, /healthz, lock and rollback window for a reader who does not know the project.
- Added a Decisions section that fixes choices the brief left open: the ALB assumption, the lock mechanism, where deploy state is stored, the migration lint rules, a 100-request floor for judging a 5xx window, and immediate abort on a smoke failure.
- Gave every step a 'Starts when', 'Does' and 'If it fails' entry, as the brief requires.
- Added the explicit order that the health gate passes before smoke tests run, and that both must finish within 10 minutes of the first instance starting.
- Added an abort step (8) for the 10-minute limit, which the draft did not have. It specifies that the public listener is not touched and that the failed instances are stopped.
- Defined the test listener, which the draft named but did not explain.
- Split the old colour's life into a rollback window (step 11) and a teardown job at T+30 (step 12), with the lock rules for each. Specified how a rollback after teardown becomes a normal deploy of the previous release.
- Moved the lock release into the watch and teardown steps, so that a deploy does not hold the lock for the whole 30-minute window while still blocking new deploys during it.
- Added a 'Where deploy state is kept' section, which the brief asked for and the draft lacked.
- Changed the wording of the migration step to explain what additive means and why the live colour keeps working, and to say how a failed concurrent index build is cleaned up.
- Defined the terms the document uses: instance, ALB, listener, target group, release, migration, smoke suite, 5xx, and Parameter Store.
- Fixed the lock. Step 1 used to hold the lock while waiting for an open rollback window to close, which would block the teardown job from taking the lock. A waiting run now releases the lock and retries later. Terms and Decisions now give one definition of the lock.
- Step 10: added the traffic-floor alert (a whole watch with no judged window) and explained that early windows cover only the time since T.
- Step 10: said that old instances are stopped only after the listener has been repointed, and that the new colour stays live if the listener change keeps failing.
- Decisions: added the rollback outcome (old colour live, candidate marked failed, rollback target cleared, window closed, no teardown). The brief did not specify this.
- Step 9: added that a failed final health check goes to abort rather than switching.
- Step 12: the teardown job now reads state first, does nothing if a rollback already happened, and stops without changing anything if the listener does not point at the new colour. It also now appears in the list of state writers, and the alert on repeated failures is stated.
- Step 12: said which release is the 'previous' one, since the rollback target is cleared at teardown.
- Step 11: explained that a manual rollback waits for the lock during the watch, so it is in practice available from T+15.
- Step 5, 6, 8 and 9: reworded for clarity. Each step now states plainly when its checks begin, what it changes and what happens on failure, without changing the procedure.
- Added a one-line description of the ALB as the single entry point for user traffic.
- Defined forward target, candidate release, rollback target and deploy state in Terms, since later steps depend on them.
- Replaced the loose phrase 'the listener uses' with 'the target group the listener forwards to' in steps 2, 9, 10 and 12, so each step names the exact change to the listener.
- Clarified in step 1 and step 11 that runs waiting for a rollback window do not hold the lock.
- Expanded the migration lint entry in Decisions from one long sentence into a list of the four rules, and said it runs before deploy.
- Named the Parameter Store record as a key-value store and gave the rollback target its own term, without changing any rule.

### Holes
- None.
