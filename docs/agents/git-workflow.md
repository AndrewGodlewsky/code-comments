# Agent checkpoints and cleanup

The user authorizes agents to commit and push their own stable checkpoints,
integrate finished work into `main`, push `main`, and clean up their task branches
and temporary worktrees without asking again. A task is complete only after all
of those applicable steps are verified. A pushed feature branch is a checkpoint.
Preserve recoverable work and other agents' ownership throughout. This is an
instruction-driven workflow, not a background scheduler.

## Start with ownership

1. Inspect `git status --short --branch`, `git worktree list`, and the configured
   remotes before changing files. Identify the current task, branch, worktree,
   existing changes, and any owner already using them.
2. Use an assigned task branch or create a uniquely named branch such as
   `agent/<task>` from the appropriate base. Keep an existing manager-assigned
   branch name. Record the branch and workspace in the task handoff or status.
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
   refs/heads/<task-branch>`). Report the branch and checkpoint commit.

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

## Integrate finished work into main

1. Review and validate the complete task changes, reconcile knowledge updates,
   commit them, and verify the pushed task branch. Confirm all task contributors
   have finished before integrating their shared branch.
2. Fetch current remote state and inspect the relationship between the task branch,
   local `main`, and `origin/main`. Include current main changes without losing
   either side's work. Resolve conflicts and rerun affected checks.
3. Integrate through the repository's required review/PR process when applicable.
   If direct integration is permitted, use an available clean integration checkout,
   switch to `main`, incorporate the fetched main and the finished task branch,
   and validate the integrated result. A fast-forward is sufficient when possible.
   Coordinate access if another agent owns the checkout; use an isolated integration
   workspace if necessary rather than switching another agent's branch.
4. Push `main` normally. If it advanced remotely, fetch, reconcile, and revalidate
   before retrying. Never force-push to complete integration.
5. Fetch again and verify that remote `main` contains the completed work. For a
   history-preserving merge, verify the task tip is an ancestor of `origin/main`.
   For a squash/rebase merge, verify the merged PR's final head and resulting
   changes against the fetched target, including any post-review commits.

A pending review, failed check, unresolved conflict, denied push, or uncertain
ownership keeps the task incomplete. Preserve the work and report the specific
blocker; continue when it can be resolved. Do not present "ready to merge" as
task completion. An explicit user request to pause, hand off, or leave a draft
can stop this workflow, with the remaining integration work stated clearly.

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

Report the integrated commit, verified remote `main`, checks performed, and task
branches/worktrees removed (or temporary worktree not applicable). Completion
requires validated work on remote `main`, deletion of the finished task's local
and remote branches, removal of its temporary worktrees, and a clean owned
checkout. If any required step remains, report the task as incomplete with the
concrete blocker. Unrelated active work is outside this task's cleanup scope.
