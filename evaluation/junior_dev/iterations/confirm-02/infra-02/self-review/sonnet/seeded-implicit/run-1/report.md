## Review of infra-02 (self-review, author sonnet, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Replaced the one-line-per-box chart with a top-down flowchart. It shows each step's trigger, its reads and writes (SSM tags, migrations, locks) and its failure path.
- Added the missing PR path, the join after parallel tests, the self-approval check, the window wait, and separate Fail, Expired and Superseded endings.
- Removed the 'kubectl rollout undo' line. It contradicted the requirement to use deploy.sh, and the script already has a rollback mode.
- Explained how deploy.sh rollback uses previous_tag and why it is run only after a staging smoke failure, not after a failed rollout. Production rollout failures now run canary-off and fail for human follow-up.
- Replaced the vague 'locks' and 'older runs get superseded' lines with concrete rules: lock scope, order of lock and window, and when and what is superseded.
- Spelled out how the canary is measured: start time, 30 s sampling, the exact Prometheus query, the 1% threshold, and fail-safe handling of missing data.
- Noted that CI restricts approval by group only, so the 'never the commit author' rule is enforced by an explicit check.
- Added what readers need from the existing files: SSM keys and when they are written, forward-only migrations and their effect on rollback and canary-off, contexts, and the shared production database.
- Replaced the bullet list with short sections: how to read the diagram, the rules shown, decisions I made, and what deploy.sh does and what to watch for.
- Added a Terms section (SHA, stable vs canary, SSM state, lock) so readers new to the repo can follow the diagram.
- Corrected the legend: arrows were described as red but no link styling exists, so dashed arrows and shaded end nodes are now described instead.
- Grouped the diagram into labelled stages (pull request, build and test, staging, approval, production) with subgraphs.
- Removed the duplicate smoke-test-fail edge to rollback and the redundant PROD/CAN/OFF wiring clutter; failure edges are gathered in one block.
- Added the missing superseded exit at the staging lock and labelled the join so it shows both test jobs must pass.
- Showed that a test failure cancels the other test job in the diagram, and when the staging lock is held and released in the staging node and notes.
- Rewrote the confusing deployment-window explanation: the window is checked after taking the lock because lock waits can be long, and the canary start counts as the production start.
- Added a short note on canary-then-stable ordering and what happens on canary or rollout failure.
- Clarified that the shared production Postgres means the canary migration affects stable pods; tightened wording elsewhere.
- Added a short 'The path in brief' section so readers get the whole flow before the diagram
- Defined 'run' and 'migration' and glossed SSM Parameter Store and the canary for readers new to the stack
- Moved the 'locks released however a run ends' note into the Terms definition
- Clarified that the author check happens after someone approves
- Said the superseded exception to announcements up front
- Reworded the rollback-tag explanation ('actually running') and merged the shared-Postgres point into the migrations bullet
- Left the Mermaid diagram unchanged to avoid breaking it

### Holes
- None.
