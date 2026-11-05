# Working in code-comments

## Start a task

For each incoming request, use [task tracking](docs/agents/task-tracking.md) to
classify its intent and select the owning task branch. Preserve unfinished tasks
when switching to independent work; only completed tasks enter closeout.

Read [intent.md](intent.md) for the user's goals and
[architecture.md](architecture.md) for the current structure and open boundaries.
For research, evaluation design, or changes to skill behavior, also read
[docs/research/README.md](docs/research/README.md).

Resolve explicitly requested skills to their actual `SKILL.md` before choosing
a workflow. Search the installed package if the visible skill catalog omits one.

## Checkpoint and clean up

Before editing, checkpointing, handing off, or cleaning up, read
[docs/agents/git-workflow.md](docs/agents/git-workflow.md). Automatically commit
and push verified checkpoints on the owned task branch. Before assigning work,
record its issue/branch ownership using [task tracking](docs/agents/task-tracking.md).
Completion requires a separate agent's review, verified remote `main` integration,
issue reconciliation, branch/worktree cleanup, and independent final audit.
Preserve the primary checkout and other agents' active work. Report blocked gates
as incomplete.

## Keep knowledge current

During work and before task completion, follow
[docs/agents/learning.md](docs/agents/learning.md). Capture durable corrections and
verified lessons in their owning files, reconcile obsolete guidance, and report
what changed. Preserve the distinction between hypotheses and demonstrated results.

## Agent skills

### Issue tracker

Track issues and specs in `AndrewGodlewsky/code-comments` on GitHub using `gh`.
Before reading or publishing tickets, read [docs/agents/issue-tracker.md](docs/agents/issue-tracker.md).

### Triage labels

Use Matt Pocock's five default triage labels. Before triaging work, read
[docs/agents/triage-labels.md](docs/agents/triage-labels.md).

### Domain docs

Use a single-context layout: root `GLOSSARY.md` and `docs/adr/`. Before exploring
the domain, read [docs/agents/domain.md](docs/agents/domain.md).
