# Code Comments: architecture

This document owns the current structural overview and the status of proposed
boundaries. Product purpose lives in [intent.md](intent.md). Update this overview
when the actual structure or a structural decision changes; keep detailed
instructions in their owning files.

## Current system

The repository contains research, agent workflow configuration, and a small
offline fixture audit/export tool and Docker trajectory diagnostic. There is no
implemented Code Comments skill, real model adapter, application runtime, or
published package. No model
experiments have been run here. Current work is offline-only by user direction.

`evaluation/offline.py` audits a trusted original fixture and exports its first
task under baseline, inline and external-context conditions. The fixture's
`private/` assets are excluded from exports but remain public development material
in this repository; this is not a security sandbox. `tests/test_offline.py` owns
automated behavioral/export checks. See the [tool guide](docs/evaluation/README.md)
and [roadmap](docs/roadmap.md) for current boundaries and remaining issues.

`evaluation/runner.py` carries code through fresh Docker workspaces, records
deterministic oracle/no-op trajectories, and guards resume with configuration
hashes, exclusive records and interruption markers. `sandbox.py` owns bounded
execution/snapshots; `grading.py` keeps expected outcomes on the host and runs
candidate calls separately. The result collector still shares the candidate's
interpreter and is not tamper-proof. See the [runner guide](docs/evaluation/runner.md)
for verified commands, boundary limitations and remaining #7 work. Docker CI
exercises the development fixture; it does not establish model efficacy.

GitHub Issues in `AndrewGodlewsky/code-comments` is the configured tracker.
Its operations and triage vocabulary are documented under `docs/agents/`.

## Knowledge ownership

| Source | Owns | Update trigger |
| --- | --- | --- |
| `intent.md` | User goals, product boundaries, and open hypotheses | An explicit change or clarification of direction |
| `architecture.md` | Current structure, responsibilities, and status of proposed boundaries | A structural change or accepted design decision |
| `README.md` | Human entry point and verified setup/check commands | Onboarding or runnable tooling changes |
| `AGENTS.md` | Short startup instructions and pointers for agents | A recurring discovery problem or workflow requirement |
| `CLAUDE.md` | Claude Code import of the common instructions | A verified client discovery requirement |
| `.github/copilot-instructions.md` | Copilot entry point to the common instructions | A verified client discovery requirement |
| `docs/agents/` | Tracker conventions, domain-document rules, checkpoint/cleanup policy, and learning workflow | A change to how work is performed |
| GitHub branch tracking issues | Branch purpose, assignments, associated issue scope, and review/closeout evidence; format in [task tracking](docs/agents/task-tracking.md) | Assignment, checkpoint, review, integration, or cleanup changes |
| `docs/research/README.md` | Evidence navigation and research status | A report is added, revised, superseded, or reproduced |
| Research reports | Source findings, limitations, and project interpretations | New evidence or a correction to a claim |
| `docs/research/evaluation-protocol.md` | Canonical proposed experiment design | An experimental design decision or measured limitation |
| `docs/roadmap.md` | Milestone order and gates, linking GitHub's live assignments/status | A change to product execution scope or dependencies |
| `docs/evaluation/README.md` | Runnable offline tools, provenance and validity limits | A verified tool or evaluation boundary changes |

Use references between these owners. A summary should point to the authoritative
detail rather than create another independently maintained specification.

## Proposed future boundaries

These responsibilities remain proposed beyond the small Python offline diagnostic.
That diagnostic does not select the final runner framework or skill languages.

| Boundary | Responsibility | Separation to preserve |
| --- | --- | --- |
| Evaluation corpus | Versioned scenarios, source context, and task sequences | Agent-visible inputs remain separate from hidden acceptance checks |
| Evaluation runner | Reproducible trials with recorded model, harness, budgets, and repository state | Comment/doc conditions receive comparable information and tools |
| Results and analysis | Raw outcomes, failures, costs, and reproducible summaries | Observations remain distinguishable from interpretations |
| Portable skill | The evidence-supported comment workflow | One canonical behavior source, with supporting references only as needed |
| Client distribution | Installation and discovery for advertised clients | Client-specific details stay outside the portable behavior where practical |

The [evaluation protocol](docs/research/evaluation-protocol.md) owns experimental
details. [Portability research](docs/research/skill-portability.md) records platform
evidence and candidate package paths. Implement these boundaries only as the
research and agreed design justify them.

## Additional files and directories

Create `GLOSSARY.md` when domain terms have been resolved. Create `docs/adr/` when
a consequential, non-obvious trade-off deserves a durable decision record. An ADR
records the reasoning; this overview records the resulting structural state and
links to it.

Create additional corpus, runner, result, skill, and CI directories with their first
actual contents. Add judgment-based review standards when there are concrete standards
to enforce; put mechanically checkable requirements in executable checks when
the relevant tooling exists. This keeps the tree representative of real work.

## Changing the architecture

Label options as proposed until a decision is made. When a proposal is accepted,
record its status and evidence, update this overview, and revise affected
instructions or research pointers in the same change. When superseding a costly
decision, retain its historical rationale through an ADR link.

Keep claims about working integrations tied to recorded checks. Documentation
research, successful installation, successful invocation, and improved coding
outcomes are different kinds of evidence.
