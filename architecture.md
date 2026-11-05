# Code Comments: architecture

This document owns the current structural overview and the status of proposed
boundaries. Product purpose lives in [intent.md](intent.md). Update this overview
when the actual structure or a structural decision changes; keep detailed
instructions in their owning files.

## Current system

The repository currently contains research and agent workflow configuration.
There is no implemented Code Comments skill, evaluation runner, application
runtime, or published package. No model experiments have been run here.

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
| `docs/research/README.md` | Evidence navigation and research status | A report is added, revised, superseded, or reproduced |
| Research reports | Source findings, limitations, and project interpretations | New evidence or a correction to a claim |
| `docs/research/evaluation-protocol.md` | Canonical proposed experiment design | An experimental design decision or measured limitation |

Use references between these owners. A summary should point to the authoritative
detail rather than create another independently maintained specification.

## Proposed future boundaries

These are candidate responsibilities for planning, not implemented modules or
accepted choices of language, framework, or directory structure.

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

Create corpus, runner, result, skill, and CI directories with their first actual
contents. Add judgment-based review standards when there are concrete standards
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
