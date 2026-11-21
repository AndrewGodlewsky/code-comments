## Review of infra-02 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Rewrote the Mermaid flowchart so the PR path, the parallel tests with their retry rule, the push step, the staging and production locks, the approval gate, the window wait, the canary watch and the canary-off steps all appear, with failure edges for each.
- Added a table giving each step's trigger, what it reads, what it writes and its failure path, since readers have not seen the repo or deploy.sh.
- Replaced the terse 'Rollout failures use kubectl rollout undo' line with the rule that smoke failures use deploy.sh rollback and rollout failures use kubectl rollout undo, and why (tags are written only after success, so deploy.sh rollback would set the wrong tag after a failed rollout).
- Replaced 'Older runs get superseded' with an explicit rule: a run is superseded when a newer run reaches approval, unless it has already started its canary.
- Stated the push point: the image is pushed after both test suites pass and before staging, so failed builds never reach the registry.
- Spelled out the approval rules (release-approvers only, not the commit author, rejection ends the run, 72-hour expiry with staging left on the new tag), the window wait rule, the canary sampling (every 30 seconds, 0.01 threshold, no-traffic failure) and the canary-off step after a successful stable rollout.
- Added the 'Terms used' section and a 'Carried over from the existing files' section covering forward-only migrations, the rollback behaviour that leaves previous_tag unchanged, and the canary not being recorded in SSM.
- Added a 'Known limits' section: laptop deploys bypass the locks, and a failed canary removal after a successful production deploy needs a person to check.
- Added a short 'Terms used below' entries for image, rollout, migration, smoke tests, deployment window, supersede and announce, and expanded SSM, stable, canary and lock so a reader without the repo can follow them.
- Added a numbered 'In order, in plain words' summary before the flowchart so the run can be read end to end before the detail.
- Flowchart: integration tests now show their one retry as a visible branch. A unit test failure now ends the run directly instead of going through a shared join node. The 'Both suites passed' step is now a plain join.
- Flowchart: the approval branch label now reads 'a newer run reached approval' instead of 'reached approval first'. A run waiting for the window can now also be superseded, matching the rules text.
- Flowchart: failure paths that end a run now name the lock they release, and the production canary and staging failure nodes are labelled accordingly. The text states that a run releases its locks when it ends. The original did not say this explicitly; it is the natural reading of named CI locks.
- Canary watch: explained that a sample with no canary traffic is empty because the 5xx ratio divides by zero requests, so the 'no traffic' rule is understood. Wording changed from 'no traffic for 2 samples' to '2 empty samples in a row' in the chart and table.
- Clarified that the 72-hour limit covers only the wait for approval, not the wait for the deployment window. The original implied this but did not state it.
- Rewrote the rollback versus undo rule in plainer words and defined ReplicaSet inline, keeping the same logic and conclusions.
- Added plain-language definitions for Kubernetes, cluster, pod, deployment, kubectl, load balancer, registry, Prometheus, 5xx error and rollout undo, since readers have not seen the stack.
- Defined SHA as the commit ID and image tag, and explained that migrations are schema changes that run before the image changes.
- Expanded the step list so each step says what happens in plain words, including the 72-hour limit and the 1 percent threshold.
- Added a short reading guide before the diagram explaining shapes, arrow labels and which failures are announced.
- Stated that the canary check takes 30 readings over 15 minutes, and that the window limits only when a production deploy starts.
- Rewrote the rollback versus undo rule in shorter sentences, with the reason SSM is wrong after a rollout failure.
- Kept the Mermaid diagram, the table, the rules and the known limits unchanged in substance, so the diagram still matches the table.

### Holes
- None.
