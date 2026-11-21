## Review of infra-01 (self-review, author sonnet, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short 'How it works in brief' section and a glossary (listener, target group, old/new colour, T, alert, final phase) so a reader new to the stack can follow.
- Fixed lock inconsistency: the concurrency group is the lock and is held from step 2 (when the run starts) to step 14; step 3 renamed 'Check the starting state' and its failure now releases the lock. Steps 2 and 4 also state lock release.
- Step 6 failure no longer circular: deadline starts when instances are started, failure means not all registered by the deadline.
- Clarified that the engineer rollback job is allowed from T (not only after step 10), and step 10 now checks phase so it exits if a rollback already happened; step 12 now starts at step 9 and runs alongside step 10.
- Step 12 rollback job now releases the lock; step 13 says the redeploy runs steps 2 to 14.
- Listed all places that stop instances to keep the 'idle colour has 0 instances' invariant accurate.
- Explained 'conditional write' and the reason for dropping/renaming columns later inline; tightened wording throughout and used 'serialised' consistently.
- Added a one-line definition of the abort procedure and of T+15/T+30 in the terms list, so readers meet them defined before first use.
- Moved the rationale for dropping/renaming columns into the intro paragraph and removed the duplicate parenthetical in step 2.
- Replaced the vague 'Step 11, step 12 (engineer rollback), step 13' reference with 'Steps 11, 12 and 13'.
- Split the dense one-deploy-at-a-time bullet into rule, why, and cost sub-bullets.
- Split step 13's long Changes entry into sub-bullets for what happens after shutdown.
- Minor wording cleanups: 'has not changed since it was read', 'taken from the load balancer's metrics', 'That job uses...' for the rollback job, and dedented the checklist sub-bullets for consistent Markdown nesting.
- Added a sentence up front that deploys run only from CI on merge, and that the service is stateless HTTP, so the system is understandable without the brief.
- Defined 'conditional write' in the terms list and gave a one-line plain explanation of 'concurrency group' and 'smoke tests'.
- Clarified what 'resumes from phase' means for a crashed job, and added the resume case to step 3.
- Step 3 failure now explicitly covers the previous deploy not being in a final phase, which was previously stated as a requirement but had no failure outcome.
- Step 5: said what the advisory lock is for.
- Step 14 and the abort procedure now point to each other so the lock release path is explicit and consistent.
- Kept all steps, ordering, numbers and the checklist format unchanged.

### Holes
- None.
