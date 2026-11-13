# Code Comments research

For source passages without evaluative synthesis, start with the
[comment-context collection](comment-context/README.md). It preserves locations,
opposing positions, examples and coverage limits from available local sources.
Use the [extraction workflow](../workflows/extract-comment-context.md) to add more.

Current phase (2026-11-09): the performance hypothesis below was tested, and the
[long-horizon pilot](../evaluation/pilot-report-2026-11-08.md) found no measurable
downstream benefit. The product is now a comment hygiene skill with no performance
claim (see the [purpose document](../skill/hygiene-skill.md)). This research remains
the record of why the hypothesis was worth testing. The [roadmap](../roadmap.md)
tracks remaining work.

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

The [imported paper collection](ai-code-comments/README.md) adds four full-text
reviews and one explicitly limited evidence brief, with source files and a
[transfer handoff](ai-code-comments/chat-context/HANDOFF.md). The
[reading-list access guide](../reading-list-access.md) indexes local books,
historical papers and external access options. These are reading resources, not
new experiments or changes to the evaluation protocol.

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
| [Candidate repositories for history replay](candidate-repos.md) | Five permissive Python repositories with post-cutoff PR windows for #19's medium and large tiers (narwhals top pick); how the #8 registry fits |
| [R1-R4 citation audit](audits/2026-11-07-r1-r4-citation-audit.md) | Independent check of 33 load-bearing claims in R1-R4: 24 verified, 8 minor issues and 1 misrepresentation, all corrected in the reports; no fabricated sources |
| [Docs for agents in practice](docs-for-agents-practice.md) | R1 (#30): practitioner docs folders, AGENTS.md studies and measured drift; how to build a realistic docs-folder arm for #19 |
| [Capability gradient](capability-gradient.md) | R2 (#31): benefit tracks headroom and knowledge the code lacks, not simply weaker models; #19 reader tiers and sample sizes |
| [Human maintenance and drift](human-maintenance-and-drift.md) | R3 (#32): docs drift faster than comments; developers read code and comments first; the human-editing claim lacks direct evidence |
| [Context layers](context-layers.md) | R4 (#33): how decision memory, instructions and code docs are divided in practice; proposed boundary for the skill |
| [Long-horizon degradation](long-horizon-degradation.md) | R5 (#35): agent code measurably erodes over successive edits; no evidence weaker models erode faster; no test of comments as the remedy |
| [Planner-executor split](planner-executor-split.md) | R6 (#36): a strong model's plan closed about 40% of a cheap model's gap; implementation holds real design decisions; hybrids that keep the strong model involved during execution work best; task-specific context helps, general repo context did not |
| [Skill portability](skill-portability.md) | Verified documentation and local tool evidence for eventual distribution across Orca, Codex, Claude Code, and Copilot |
| [Junior-dev evidence review](../junior-dev/research-2026-11-12.md) | Separate product (#52): whether a novice questioner improves an agent's plans and diagrams. The premise holds (LLM diagrams get relationships wrong); the mechanism is untested and weakest where the author's answers go unchecked; proposed eval with same-budget controls |

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
  - First evidence: the [2026-11-08 long-horizon pilot](../evaluation/pilot-report-2026-11-08.md).
    Over six real narwhals PRs, the lean comments skill did no better than a
    one-sentence instruction, and no arm caused a regression.
  - Its limit: only one of the six steps separated the arms, so this is weak evidence
    of no effect.
- Whether less capable models become sufficiently reliable at a lower total cost.
  - In the same pilot, Haiku came within noise of Sonnet and was about 4× cheaper per
    passing step, with the full test suite available.
  - Still open: longer chains, weaker test suites, and erosion that tests can't catch.

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
