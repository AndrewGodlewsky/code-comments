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

## The user's fuller theory (stated 2026-11-07)

The user stated this from experience. It is intuition to test, not an established
result, and they asked for evidence that it holds.

In large or complex codebases that change often, an AI coding workflow needs three
kinds of context:

1. **Localized decision memory.** It restores *why* decisions were made and which
   alternatives were rejected.
2. **Instructions and intent.** Repository guidance and the product's purpose.
3. **Documentation of what the code does.** The user has found it very helpful to have
   the AI generate documentation alongside the code, in a `docs/` folder. On larger
   projects, the AI seems less likely to get a future change wrong when it can
   consult that documentation.

**The skill targets the third layer.** A docs folder creates **two sources of truth**:
the code, and a description of the code. Keeping them in sync is too much work.
Nobody knows which documents a change affects, so they drift. The user expects human
engineers in particular not to update the docs.

Further claims to test:
- **Model capability.** Frontier models need such documentation less, because they
  read and understand the code directly. Weaker models genuinely struggle without the
  extra context, especially about effects and relationships ("this code affects that,
  relates to this").
- **Human editors.** AI will do most code editing, but when a human engineer must
  change the code, it will be very hard without comments.
- **Placement.** Inline comments at the point of change are more likely to be read
  and kept current than a separate folder, by agents and humans alike.

**Scope clarification (user, 2026-11-07).** The skill is **not** a memory system and
must not take control of one. Decision memory is a separate layer the user will
maintain in their projects. The skill's mechanism is only this:
- **Point of edit.** An agent must open a file to change it, so context written in
  that file's comments is seen exactly when it matters. The user's core intuition is
  that this extra context at the point of edit significantly improves edit quality
  and prevents mistakes.
- **Searchable placement.** When an agent needs context from elsewhere, comments
  beside the code they describe are easy to find with `grep` or other search tools.

No generated index, central store or lookup service is part of the skill. An
earlier proposal to generate a docs index from comments was dropped. The user's
reasons:
- **The code is the source of truth**, because it is what runs.
- **Human editors break indexes.** A person changing code by hand won't know to
  regenerate an index, and if regeneration needs an AI run that someone forgets,
  the project is out of sync again. That is the core failure the project exists
  to remove.

See [ADR 0001](docs/adr/0001-context-lives-inline-no-central-index.md) and the
[trade-off analysis](docs/skill/inline-only-tradeoffs.md). Revisit discovery aids
only if evaluation shows agents missing context in other files, and then only in a
form that manual edits cannot leave out of sync.

**Stored idea (later priority):** a consistent tag or syntax convention for
explanatory comments (`WHY:`, `CONSTRAINT:`, `SEE:`), so `grep` and `ripgrep`
retrieval is fast and precise without any index (#34).

**What this means for evaluation.**
- The primary comparison is **inline comments maintained by the skill** against the
  user's current practice, **an AI-maintained docs folder**, over a *sequence* of
  changes. Drift is part of the outcome, not a nuisance.
- Success is measured on the *next* agent's work. In particular, a **weaker reader**
  model must make correct follow-up changes, whichever model wrote the context.
- Comment-quality scores are guardrails, not the goal.
- The user is open to testing small, medium and large codebases of varying
  complexity, and can supply a real codebase if needed.

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
automatically so it remains recoverable across sessions. Agents should interpret
incoming requests by task intent: continuations and scope adjustments stay with
the existing task, while independent work gets its own branch. Switching tasks
does not complete the previous one. Unfinished branches and worktrees remain
available with enough recorded context to resume; cleanup applies to completed
tasks. The routing procedure lives in [task tracking](docs/agents/task-tracking.md).

The user defines task
completion as independent verification of the entire branch purpose, integration
into remote `main`, reconciliation of associated issues, and removal of the task's
local/remote branches and temporary worktrees. A separate agent reviews before
integration and audits closeout. GitHub tracking issues retain branch assignments,
scope, and evidence across sessions. Agents are authorized to
carry that lifecycle through without another permission request, subject to
required checks and repository protection. Preserve the primary checkout and
other agents' active work. The operational rules live in
[docs/agents/git-workflow.md](docs/agents/git-workflow.md).

## Decisions still open

Current execution constraint (2026-11-05): the user chose **offline work only**
when asked about the first model smoke-run budget. Continue local development
and validation; do not start model campaigns until the user changes that direction.

Update (2026-11-07): the user approved one **small paid pilot** of the skill-variant
tournament. It runs 3 eval cases x 6 arms (five variants and a no-skill control)
x 1 rep through headless Claude Code, capped at $1 per attempt. Its purpose is to
validate the wiring and measure cost; it produces no efficacy claim. The full
tournament (#26) needs a separate approval based on the measured pilot cost.
Offline-only otherwise still applies.

Update (2026-11-07, later): after the pilot ($0.57), the user approved the **full
tournament**. It runs 20 cases x 6 arms x 3 reps on both `claude-sonnet-5-5` and
`claude-haiku-5-5`, projected at about $12-14 with a $1 cap per attempt. Further
campaigns still need their own approval.

Update (2026-11-07, later): the user approved a **#19 stage-1 smoke run**: 10
sequences x 3 arms (code-only, docs-folder, inline:lean) x 1 rep, with a Sonnet 5.5
writer and a Haiku 5.5 reader, estimated at $1-2. Larger stage-1 or stage-2 runs
need their own approval.

**Correction (2026-11-07):** this round was earlier described as using Haiku to
represent "the less capable model the hypothesis is about". That was wrong. In
that run, Haiku *wrote* the comments. The hypothesis concerns weaker models *reading*
context and making later changes. The round tests the skill's writing behaviour
only (see `docs/skill/tournament-2026-11-07.md`).

Update (2026-11-09): the long-horizon pilot (#37,
[report](docs/evaluation/pilot-report-2026-11-08.md)) found **no measurable downstream
benefit** from the skill. The product was narrowed to a **comment hygiene** skill:
keep comments true, record reasons the code cannot show, never invent a reason, and
add no noise. It makes no performance claim. It ships as a Claude Code plugin (#45),
and Orca, Codex and GitHub Copilot are parked. It activates the way Claude Code skills
do, when its description matches the request; whether that happens is being measured
(#20). The user approved paid runs for the activation eval (#20) and the wider hygiene
eval (#21), with the estimated and actual cost to be reported.

The [roadmap](docs/roadmap.md) links the remaining work.

The paragraph below is the founding position. The 2026-11-09 update above settles
activation (the skill loads on demand, from its description) and packaging (a Claude
Code plugin) for now.

Research and experiments should inform activation, comment categories, language
coverage, model selection, corpus selection, release thresholds, and the balance
between inline context and separate documents. Neither an always-on writer nor
an on-demand audit has been chosen. Packaging and runtime details are also open.

For current repository structure and proposed future boundaries, read
[architecture.md](architecture.md). For evidence and its limitations, start at
[docs/research/README.md](docs/research/README.md).
