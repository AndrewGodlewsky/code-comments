# Code Comments: intent

This is the authoritative record of the user's product direction, captured from
the founding conversation on 2026-11-04. It describes goals and hypotheses, not
demonstrated results. Update it when the user changes the direction; keep research
findings and implementation details in their own sources.

## The problem

AI-assisted development often produces code first and explanatory documentation
afterward. The explanation lives in a separate folder and must be synchronized
with the implementation. As a project evolves, this creates maintenance work and
competing accounts of how the system works.

The user experiences this problem personally. They want important context to
remain close to the source that future agents will read and modify, reducing the
need to reconstruct decisions or consult a separate description of the same code.

## The intended product

Create a reusable skill named **Code Comments**, easily downloadable and usable
through Orca, Codex, Claude Code, and GitHub Copilot.

The skill should help preserve valuable explanation in source code: what a
meaningful piece of code accomplishes, why it takes its present form, relevant
constraints, and relationships a future editing agent needs to understand.
The aspiration is for this to become a natural part of AI-assisted development.
The exact activation and maintenance workflow remains undecided.

The value sought is context that improves future work. Comment quantity is not
the objective, and the user has not requested a comment on every line or function.
Code remains the source for implemented behavior; explanatory comments must stay
accurate as that behavior changes.

## The hypothesis to investigate

Selected, well-maintained inline explanations may replace some shared documents
and help less capable models achieve better, more consistent results over a
long-running project when editing code.

This combines several questions that require separate evidence:

- Does supplying the relevant knowledge improve editing outcomes?
- Does placing it beside code improve discovery or use compared with equivalent
  knowledge in accessible documents?
- Can agents maintain that knowledge through successive changes and fresh sessions?
- Which kinds of shared documentation can be replaced without losing useful context?
- Do improvements persist for less capable models, with worthwhile total cost
  after writing, updating, retrieving, and correcting the explanations?

Selective replacement is the goal. Research records, installation guidance,
product intent, and other documents can retain distinct purposes. The exact
replacement boundary is part of the investigation.

## Research before workflow decisions

The user explicitly wants substantial research and data before deciding how the
skill should operate. Historical books and articles about the purpose and quality
of code comments are important inputs. The intuition that older programming
practice may offer useful lessons should be examined against primary sources,
including conflicting advice and limits of the evidence.

Empirical studies of humans, code comments, coding models, and long-term
maintenance answer different questions. Our experiments must test the actual
product hypothesis. Positive, null, and negative results are all useful; the
project should be able to revise or reject its starting intuition.

Judge success by correct subsequent changes, preserved constraints, regressions,
consistency across runs, and total effort or cost. Keep the information in comparison
conditions equivalent so that better information is not mistaken for better
placement. Detailed experimental controls belong in the
[proposed evaluation protocol](docs/research/evaluation-protocol.md).

## Development experience

The repository should retain useful lessons across sessions. As development
proceeds, agents should update the relevant instructions and context from user
corrections, observed failures, verified findings, and real design decisions.
This knowledge should remain concise, traceable, and easy to revise.

The learning process is defined in [docs/agents/learning.md](docs/agents/learning.md).
It maintains repository knowledge through explicit file changes that can be
reviewed in Git. The user wants this maintenance to happen as part of normal work.

With multiple agents contributing, stable progress should be committed and pushed
automatically so it remains recoverable across sessions. The user defines task
completion as verified integration into remote `main` followed by removal of the
task's local/remote branches and temporary worktrees. Agents are authorized to
carry that lifecycle through without another permission request, subject to
required checks and repository protection. Preserve the primary checkout and
other agents' active work. The operational rules live in
[docs/agents/git-workflow.md](docs/agents/git-workflow.md).

## Decisions still open

Research and experiments should inform activation, comment categories, language
coverage, model selection, corpus selection, release thresholds, and the balance
between inline context and separate documents. Neither an always-on writer nor
an on-demand audit has been chosen. Packaging and runtime details are also open.

For current repository structure and proposed future boundaries, read
[architecture.md](architecture.md). For evidence and its limitations, start at
[docs/research/README.md](docs/research/README.md).
