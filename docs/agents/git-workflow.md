# Agent checkpoints and cleanup

The user authorizes agents to commit and push their own stable checkpoints,
integrate finished work into `main`, push `main`, and clean up their task branches
and temporary worktrees without asking again. A separate agent must verify the
whole task before integration and audit closeout afterward. A task is complete
only after all applicable steps are verified. A pushed branch is a checkpoint.
Preserve recoverable work and other agents' ownership throughout. This is an
instruction-driven workflow, not a background scheduler.

## Start with ownership

1. Inspect `git status --short --branch`, `git worktree list`, and the configured
   remotes before changing files. Identify the current task, branch, worktree,
   existing changes, and any owner already using them.
2. Use an assigned task branch or create a uniquely named branch such as
   `agent/<task>` from the appropriate base. Keep an existing manager-assigned
   branch name. Before editing, delegating, or switching tasks, follow the request
   routing and unfinished-work rules in [task tracking](task-tracking.md).
   Establish the durable issue-to-branch assignment and keep it current through
   closeout. Record the workspace in the local handoff.
3. Independently editing agents should have separate task branches and worktrees.
   Reuse an appropriate owned workspace rather than creating redundant ones. Use
   the native workspace manager when one manages the worktree.
4. When agents intentionally share a worktree, designate one agent to perform
   commits, pushes, branch switches, and cleanup. Other agents report their changes
   to that owner; they do not independently mutate shared Git state.

Preserve pre-existing or unattributed edits. Stage only changes belonging to the
task, using explicit paths or selected hunks. Overlapping edits require
coordination before staging. Do not reset, stash, or discard someone else's work
to obtain a clean tree.

## Commit and push stable checkpoints

A stable checkpoint is a coherent unit of progress with its relevant checks
passing and its diff reviewed. Examples include a verified fix, a working feature
slice, or a research/documentation update whose claims and links were checked.
For documentation-only work, use applicable document checks rather than inventing
an application test command.

Checkpoint after each meaningful stable unit and before a handoff, session end,
or task completion. During a long task, assess progress periodically instead of
deferring all commits until the entire objective is finished. Avoid empty commits
and commits consisting only of incidental churn.

For each checkpoint:

1. Run the applicable checks, review the diff, and include relevant knowledge
   updates from the [learning workflow](learning.md).
2. Stage the intended changes, inspect the staged diff, and run
   `git diff --cached --check`. Keep secrets, local environment files, and
   disposable generated output out of commits.
3. Commit with a message describing the coherent change. Do not label unverified
   work as passing or complete.
4. Push the explicit task branch to the intended remote. On the first push, set
   its upstream with `git push --set-upstream origin <task-branch>`; later use
   `git push origin <task-branch>`. Verify the remote URL before the first push.
   Publish task branches rather than pushing directly to `main` by default.
5. Verify the push succeeded and the remote branch tip matches the local commit
   (for example, compare `git rev-parse HEAD` with `git ls-remote --heads origin
   refs/heads/<task-branch>`). Record the checkpoint in the tracking issue.

A rejected push is unresolved work. Fetch and inspect divergence; coordinate if
another agent has written to the branch. Use a history-preserving resolution and
rerun affected checks. This policy does not authorize force-pushing, rewriting
shared history, or bypassing branch protection. Finish integration using the
process below and satisfy any required review or CI checks.

If a session must stop before a stable point, preserve meaningful work in a clearly
marked WIP commit on the owned task branch and push it when possible. Record the
failing or unrun checks and next step in the handoff. Treat this as recovery data,
not a verified checkpoint. If pushing is unavailable, retain the local branch and
worktree, report the exact failure and commit, and retry when access is restored.
An unpushed commit, local stash, or untracked file is not a remote backup.

## Independent completion review

When the entire branch purpose is implemented, finish and push the final
checkpoint, confirm contributors have stopped editing, and fetch remote `main`.
Incorporate current main into the task branch if necessary, resolve conflicts,
rerun affected checks, and push the resulting candidate before review.

Spawn a separate agent with fresh context that did not implement the task. Give
it the tracking issue, all associated issues, exact pushed head SHA, fetched main
SHA, relevant instructions, and validation evidence. The reviewer works read-only;
the coordinator retains Git and tracker mutation ownership. Require it to:

1. Read the instructions and issue bodies/comments independently. Compare the
   entire branch diff and delivered behavior with every acceptance criterion.
2. Inspect changes and reproduce applicable checks. Distinguish observed results
   from untested assumptions; report missing work, regressions, and stale guidance.
3. Reconcile every associated issue using [task tracking](task-tracking.md),
   identifying which can close after integration and which must remain open.
4. Return a pass or blocking findings, with the exact head and main SHAs, evidence
   for each criterion, and a proposed issue disposition and cleanup inventory.

Record the review in the tracking issue. Fix blocking findings, push, and obtain
another independent review of the updated candidate. Approval applies only to
the reviewed head and main SHAs and acceptance criteria: any new commit, target
movement, conflict resolution, or scope adjustment requires updated checks and
renewed review before integration. If a
separate agent is unavailable, retain the checkpoint and report review blocked;
self-review does not satisfy this gate.

## Integrate reviewed work into main

1. Confirm independent review passed for the current acceptance criteria,
   required checks passed, and contributors
   have finished. Fetch and verify the task tip and `origin/main` still match the
   reviewed SHAs. Return to review if either changed.
2. Inspect local `main` and its relationship to the reviewed candidate. Preserve
   any additional local work; coordinate its ownership before integration.
3. Integrate through the repository's required review/PR process when applicable.
   If direct integration is permitted, use an available clean integration checkout,
   switch to `main`, incorporate the fetched main and the finished task branch,
   and validate the integrated result. A fast-forward is sufficient when possible.
   Coordinate access if another agent owns the checkout; use an isolated integration
   workspace if necessary rather than switching another agent's branch.
4. Push `main` normally. If it advanced remotely, fetch, reconcile, revalidate,
   and renew independent review before retrying. Never force-push to integrate.
5. Fetch again and verify that remote `main` contains the completed work. For a
   history-preserving merge, verify the task tip is an ancestor of `origin/main`.
   For a squash/rebase merge, verify the merged PR's final head and resulting
   changes against the fetched target. Any integration changes beyond the reviewed
   candidate require checks and independent review before publishing.

Record integration evidence and reconcile issue states according to
[task tracking](task-tracking.md), keeping the tracking issue open for cleanup.

A pending review, failed check, unresolved conflict, denied push, or uncertain
ownership keeps the task incomplete. Preserve the work and report the specific
blocker; continue when it can be resolved. Do not present "ready to merge" as
task completion. A switch to independent work may leave the prior task unfinished
under the [task tracking rules](task-tracking.md). An explicit user request to
pause, hand off, or leave a draft can also stop this workflow, with the remaining
work stated clearly. Retained unfinished branches/worktrees are expected; cleanup
targets tasks that have fulfilled their purpose and passed the integration gates.

## Clean up after integration

Stop temporary processes started for this task and remove task-owned disposable
files after preserving deliverables and useful experiment evidence. Inspect the
final status so unexplained leftovers are visible. Preserve unmerged work while
resolving a blocker; it does not satisfy the completion criterion.

After verified integration, clean up the task branch and its temporary worktree:

1. Fetch current remote state. Confirm the branch belongs to this task, has no
   unpushed or post-review commits, and is no longer used by an agent or open work.
   Confirm integration into the intended target, not merely a closed PR or an
   old/inactive branch name. An ancestry check against the fetched target is one
   way to establish integration for a merge that preserves commits.
2. Inspect staged, unstaged, untracked, and relevant ignored files. Preserve any
   unique work or results before removal. Keep a branch or workspace whose status
   is uncertain and explain the specific reason in the handoff.
3. Leave a temporary worktree before removing it. Use its manager's supported
   removal operation, or `git worktree remove <exact-path>` for a plain Git
   worktree. Verify the resolved absolute path is the task-owned temporary
   worktree. Preserve the primary checkout and other agents' workspaces.
4. Delete the verified integrated remote task branch if it still exists and is
   unchanged, then delete its local branch with `git branch -d <task-branch>`.
   If deletion is refused (for example after a squash merge), investigate the
   integration evidence instead of forcing deletion to make the list look clean.
5. Recheck branch/worktree listings and local status. Prune obsolete metadata only
   after confirming its workspace was actually removed; a temporarily unavailable
   or locked worktree is not evidence that it is abandoned.

The integrating agent owns this cleanup before reporting completion. Keep the
primary checkout on `main` when it is owned and available. If no temporary
worktree was created, record cleanup as not applicable; never remove the primary
checkout to satisfy the rule. Leave other agents' active branches and worktrees
alone. Never use forced worktree removal, `git clean -fd`, or `git branch -D` as
routine cleanup.

## Completion report

After cleanup, send the separate reviewer the integration SHA and issue/cleanup
evidence for a read-only final audit. It must verify remote `main` contains the
reviewed work, associated issues have the correct disposition, finished task
branches and temporary worktrees are gone, and the owned checkout is clean.
The tracking issue remains open pending this audit and its final closure; record
that expected state explicitly. Fix any findings and repeat the audit as needed.
Then record the passing audit, close the tracking issue, and read back its state.

Report the integrated commit, independent review result, checks, issue closures
or justified open remainders, and removed branches/worktrees (or temporary worktree
not applicable). Completion requires every gate above, including verified closure
of the tracking issue. Otherwise report the concrete remaining blocker. Unrelated
active work is outside this task's cleanup scope.
