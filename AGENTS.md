# Working in code-comments

## Start a task

Read [intent.md](intent.md) for the user's goals and
[architecture.md](architecture.md) for the current structure and open boundaries.
For research, evaluation design, or changes to skill behavior, also read
[docs/research/README.md](docs/research/README.md).

Resolve explicitly requested skills to their actual `SKILL.md` before choosing
a workflow. Search the installed package if the visible skill catalog omits one.

## Checkpoint and clean up

Before editing, checkpointing, handing off, or cleaning up, read
[docs/agents/git-workflow.md](docs/agents/git-workflow.md). Automatically commit
and push verified checkpoints on the owned task branch. Retire completed task
resources after verifying preservation, integration, and inactivity; protect
other agents' work and retain unmerged branches with an explicit handoff.

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
