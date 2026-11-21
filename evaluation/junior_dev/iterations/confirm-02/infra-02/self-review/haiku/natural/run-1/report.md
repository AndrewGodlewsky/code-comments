## Review of infra-02 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short terms section defining SHA, image, migration, stable deployment, canary, lock, smoke test, superseded and 5xx ratio, for readers who do not know this stack.
- Opened the introduction with what the pipeline is for and what SSM holds, in plain sentences.
- Shortened the flowchart labels and made each step's trigger, reads and writes, and failure path easier to find.
- Made the integration retry a visible step. The original only showed its final failure.
- Added the missing page-a-human paths for a failed staging rollback and a failed production recovery, and a separate path for a failed canary-off.
- Split canary-off into two nodes, one after success and one after failure, so the two outcomes are not mixed.
- Replaced the 'descends from' wording with the actual check (current_tag is an ancestor of the SHA, or the same commit) and stated it for both environments.
- Explained superseded as 'not newer than what the environment already runs', and marked those exits as quiet.
- Fixed the garbled 'three usable-free samples' to 'three unusable samples in a row', and defined a usable sample.
- Stated the rule that a failure in one test suite stops the other suite. This was implied before but not written down.
- Clarified that the approval clock has no separate limit once approved, and that a superseded check is the only thing that ends such a run.
- Rewrote the decisions and constraints in plainer sentences. All eight decisions and the five open questions are kept, and the reasoning for the rollback rule is spelled out.
- Clarified the reading notes: colours, locks, tags, test failures and the page-a-human cases each have their own line.
- Added a plain-language summary and a 'What exists today' section, so a reader who has never seen the repo or `deploy.sh` can follow the plan. It lists the commands, the SSM keys, the CI features relied on, and the release policy.
- Added a 'Terms used' section defining commit SHA, image, migration, stable, canary, lock, smoke test, superseded, 5xx ratio and usable sample.
- Fixed a contradiction: the terms said a run that is not newer is superseded, but decision 1 lets the same commit pass. The definition now says a same-commit run redeploys the same tag, and the diagram question matches that.
- Clarified the deploy window: a start from Monday to Thursday, from 09:00 up to 15:00 UTC. The source said '09:00 to 15:00' without saying whether 15:00 itself counts.
- Made explicit that the 72-hour limit covers only waiting for approval. An approved run waiting for a window has no time limit and ends only through the superseded check.
- Stated that the canary watch needs a second Prometheus query (request count) for the 100-request floor, since the given query returns only the ratio.
- Added the recovery side effect to the open questions: `deploy.sh production <current_tag>` overwrites `previous_tag` with the current tag, which loses the older rollback target. The design itself is unchanged.
- Noted that a failed staging or production deploy is not rolled back automatically, and that a `canary-off` failure after a successful production deploy leaves production on the new tag.
- Added an open question about how 'page a human' is done, since the plan does not name a channel or person.
- Rewrote the flowchart labels to be shorter and clearer. The structure, triggers, reads and writes, failure paths and colours are unchanged, and the Slack #deploys announcements and Prometheus query are kept.
- Reworded the diagram reading notes into plain sentences and added a note on failed deploys, so readers do not have to infer the rollback behaviour from the flowchart.
- Added a numbered list of the eight stages in plain order under the Summary, so a reader can follow the flow before reading the diagram.
- Expanded the Summary's plain-English opening: CI, the Kubernetes and deployment terms, and the 'reaches production' sentence now say what each piece is.
- Rewrote 'What exists today' with short definitions of pods, deployments, rollouts, the registry, the Postgres service container, and Prometheus, and split the state, tests and CI facts into clearer bullets.
- Added definitions to Terms used for tag, ancestor and superseded. Rewrote 'superseded' so it matches the ancestor check in Decision 1 and states the same-commit case plainly.
- Corrected 'How to read the diagram': the old text said every box's first line names its trigger, which is not true for most steps. It now says steps follow the step before them, and that trigger lines appear on the boxes that start or wait.
- Added a note that the integration retry is the one case where a failing suite does not end the run at once.
- Added an open question that the brief's 'at any point' 1% rule is narrower in this plan, since only usable samples can trigger it.
- Left the Mermaid flowchart unchanged so its logic stays exactly as the plan wrote it. Decisions, rules and the remaining open questions keep their original wording.

### Holes
- None.
