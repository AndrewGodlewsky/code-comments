# Code Comments research

Current phase: investigate the hypothesis before deciding the skill's workflow.
No skill implementation or model experiments have been completed.

Start with the [2026-11-05 deep-dive synthesis](deep-dive-summary.md) for the
problem breakdown, evidence assessment, existing systems, benchmark shortlist,
and review order. The expanded review includes counterevidence and a proposed
statistical/cost design; it does not claim the product hypothesis is established.

## Research question

Can selected, well-maintained code comments replace some separate shared
documentation and help less capable models produce more reliable changes across
a long-running project?

This requires evidence about information, placement, retrieval, maintenance,
model capability, and total cost. A positive result for one of these does not
establish the others.

## Reading map

| Read | Purpose |
| --- | --- |
| [Deep-dive synthesis](deep-dive-summary.md) | Human review guide: what the problem contains, what is supported, who is working on it, and what would justify a product claim |
| [Direct comment evidence, expanded](comment-context-deep-dive.md) | Primary-source checks, additional interventions and maintenance studies, null/harm findings, and reporting/access limitations |
| [Related systems and researchers](related-systems-and-researchers.md) | Existing inline writers, rationale skills, generated documentation, retrieval and memory systems; capabilities distinguished from outcome evidence |
| [Benchmark landscape](benchmark-landscape.md) | Longitudinal and diagnostic benchmarks, current versus paper versions, artifacts/rights, grading hazards, and proposed reuse |
| [Historical foundations](historical-comment-design.md) | Selected passages from eight historical primary works; competing ideas about good explanation, precise access limits, and candidate comment categories |
| [Human comprehension and maintenance evidence](comment-maintenance-and-evaluation.md) | Three empirical studies, limits on generalization, and candidate evaluation fixtures |
| [Coding-agent evidence](agent-context-evidence.md) | Eight empirical papers distinguishing single-task effects, training, retrieval, repository instructions, and successive edits |
| [Proposed evaluation protocol](evaluation-protocol.md) | Canonical draft design: matched knowledge, repeated changes, cluster-aware analysis, practical/noninferiority thresholds, pilot stages, costs, and decision gates |
| [Skill portability](skill-portability.md) | Verified documentation and local tool evidence for eventual distribution across Orca, Codex, Claude Code, and Copilot |

The literature reports contain citations and separate findings from our
interpretations. These are targeted reviews, not an exhaustive systematic review.
Historical authors were read in selected passages, not as whole books. Published
results have not been reproduced locally. Compatibility documentation is not an
integration-test result.

## What remains open

- Whether useful knowledge helps because it is present, because it is beside
  the edited code, or because it is more likely to be retrieved there.
- Which facts can replace external documentation without losing global context.
- Whether a skill can write and maintain accurate explanations using evidence
  actually available during development.
- Whether any benefit persists through successive code changes and fresh sessions.
- Whether less capable models become sufficiently reliable at a lower total cost.

## Recommended repository work, in order

1. Extend or challenge the evidence map where it leaves these questions unresolved.
   Record methods, negative results, limitations, and publication versions.
2. Agree the experiment protocol and choose an initial corpus with known
   requirements and independent acceptance checks.
3. Build a reproducible evaluation runner and preserve raw results, model/tool
   versions, costs, and failed runs. Keep reviewer-only expectations out of the
   agent's workspace.
4. Add CI for actual mechanical checks: corpus validity, document links, runner
   checks, and eventually skill/package validity. Add judgment-based review
   standards only as the research or observed failures justify them.
5. If outcomes support a useful workflow, implement one canonical skill, choose
   its distribution license, and test each advertised client. Keep adapters thin.

The existing `AGENTS.md` is the navigation entry point. Additional instruction
files should expose necessary guidance to a particular client while referring
back to canonical sources. The proposal is not to maintain four independent
copies of the skill or four separate sets of project policy.

## Using Matt's skills

The installed `ask-matt` router identifies `research` for gathering evidence and
`grill-with-docs` for settling design questions in a repository. The initial
`setup-matt-pocock-skills` configuration is complete. Research comes first here;
the design interview should use this evidence when the user is ready. Later,
`retro` can turn observed process failures into checks or focused instructions.

This order records the user's research-first preference. It does not commit to
always-on commenting, an on-demand audit, a language, a model, or an installer.
