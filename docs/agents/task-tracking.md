# Task and branch ownership

Before assigning implementation work or editing a task branch, create or reuse a
GitHub tracking issue for that branch's purpose. Read the
[tracker conventions](issue-tracker.md) for operations. The tracking issue is the
durable assignment record; local handoffs and PRs link to it.

## Route each incoming request

Compare the request's intended outcome with the active task's purpose, acceptance
criteria, and associated issues. Consult existing assignments when the request
may belong to another task. Classify by purpose, not by chat boundaries, shared
filenames, or the branch currently checked out:

| Request | Action |
| --- | --- |
| Continuation: another step, correction, or clarification toward the same outcome | Continue on that task's existing branch; resume its recorded workspace if needed. |
| Scope adjustment: the user changes the requirements of the same task | Keep its branch; update criteria and associated issue scope, recording the user direction and remaining work before proceeding. |
| Independent task: a distinct outcome outside the existing task's purpose | Use its existing assignment if one exists; otherwise create a tracking issue and a separate branch from fetched `origin/main`. |

Use judgment without asking for routine confirmation. Ask only when ambiguity
materially changes scope or ownership and available context cannot resolve it.
Answer informational/status questions without creating work or switching branches
unless they also request a change. A new message alone does not finish the active
task. If a related task was already merged and cleaned up, create a linked follow-up
issue and branch from current main; preserve the completed task's historical record.

Record routing decisions when they change ownership or scope; ordinary continuation
can use the next checkpoint comment. A scope change invalidates completion approval
even when the code SHA has not changed: review against the revised criteria before
integration. Do not drop unfinished criteria merely to declare completion.

## Switch away from unfinished work

Before switching, checkpoint and push the outgoing task using the
[Git workflow](git-workflow.md), including its WIP recovery procedure if necessary.
Record remaining criteria, checks, latest commit, branch/workspace, owner, and next
step in its open tracking issue. If this agent stops working on it, mark it
`waiting` with the reason; if another owner continues, retain its active state.

Keep unfinished branches and their worktrees available for resumption. Changing
focus, inactivity, a clean checkout, or starting another branch is not evidence
of completion and does not authorize merging, closing, or deleting the old task.
If its purpose is actually fulfilled, carry it through the normal independent
review and closeout instead of leaving completed resources behind.

Use a separate owned workspace when outstanding edits, another agent, or workspace
manager constraints prevent safely switching a clean checkout. Keep incomplete
changes out of the new branch. If the new task depends on unfinished work, record
the dependency and ownership explicitly; resolve that dependency before starting
dependent implementation rather than silently including the unfinished branch.
On return, follow the recovery procedure below and resume the same assignment.

## Assignment record

Keep these fields in the tracking issue body:

```markdown
## Purpose and acceptance criteria
<Branch objective and checkable criteria for the entire task>

## Branch assignment
- Repository: AndrewGodlewsky/code-comments
- Branch: <exact branch name>
- Target: main
- Coordinator: <agent/session identity and GitHub assignee>
- Workspace: <primary checkout or workspace-manager identity>
- State: <assigned | implementing | waiting | reviewing | integrating | cleaning | complete | blocked>

## Associated work
| Issue | Scope assigned to this branch | Other owning branches | Closure condition |
| --- | --- | --- | --- |
| #<number> | <deliverable, or the tracking issue itself> | <none or links> | <full issue acceptance criteria> |

## Evidence
<Links to checkpoint, review, integration, and final audit comments>
```

Use `agent/<issue-number>-<task>` for a new branch when practical; preserve an
existing assigned name. Record the exact name either way. Keep private absolute
workspace paths in the local handoff; identify workspaces through the manager and
`git worktree list`. A single-issue task needs only its own tracking issue.

Before claiming existing work, read the issue body and comments, inspect ownership
and blockers, and coordinate any existing assignment. The GitHub assignee alone
does not identify an agent: several agents may share the same account. Designate
one coordinator to update the assignment record and mutate each shared branch.
Reread the issue before editing its body to preserve concurrent updates.

When splitting work across branches, create a tracking issue for each branch and
cross-link parent/child tasks. Record the scope and branch on both the branch's
tracking issue and each associated issue. Before delegating, give the agent the
tracking issue, branch, assigned scope, and coordinator. Update both records when
assignments change; preserve the history of transfers in a comment.

## Checkpoints and recovery

At each pushed checkpoint or handoff, comment with the branch and commit, completed
criteria, checks and results, remaining work/blockers, and next owner. Keep the
assignment fields current. Record new issues and scope changes as they arise.
Use `Refs #<number>` in commits or PRs to aid discovery; the issue record remains
authoritative. Reserve closing keywords for issues whose full scope is delivered.

On resuming, recover context from the tracking issue and comments, then compare
the recorded branch/commit with current Git state. Resolve stale ownership or
unrecorded commits before continuing. If GitHub is unavailable, retain a local
handoff and push recoverable work where possible; reconcile the durable record
before review or completion.

## Issue reconciliation

The independent reviewer follows the [Git workflow](git-workflow.md). Reconcile
the assignment table against the actual diff, commits, PR, child/dependency links,
and issues created during the task. A mention alone does not authorize closure.
For every associated issue, record whether all its criteria are delivered and
what evidence supports closure, or which scope and branch still own the remainder.

After verified integration into remote `main`, post evidence and close each fully
delivered issue, then read back its state. Check any automatic closures against
the same criteria and correct premature closures with an explanation. Keep a
shared parent or partially delivered issue open with its remaining acceptance
criteria and ownership. An unfinished criterion of this branch's agreed purpose
blocks completion; moving it to a follow-up does not silently reduce that purpose.
Record an explicit agreed scope change if one is needed.

Keep the branch tracking issue open through cleanup. After the separate agent's
final audit passes, record that audit, mark the tracking issue complete, close it,
and verify its closed state. If this is the only associated issue, this is its
closure point. Pure discussion or decision issues with no branch deliverable can
close when their recorded outcome satisfies their criteria.
