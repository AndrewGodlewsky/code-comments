# From research to a validated Code Comments skill

The product is unfinished. [Parent issue #4](https://github.com/AndrewGodlewsky/code-comments/issues/4)
owns the remaining intent; child issues own separate branches. GitHub is the
live status/assignment source. This document records sequence and decision gates,
not a second completion ledger. Research #3 is closed background.

| Work | Issue | Prerequisite / completion evidence |
| --- | --- | --- |
| Offline fixture foundation and this roadmap | [#5](https://github.com/AndrewGodlewsky/code-comments/issues/5) | Audited original fixture, equivalent context exports, regression controls and local checks |
| Freeze smoke configuration and spending cap | [#6](https://github.com/AndrewGodlewsky/code-comments/issues/6) | User budget/access, model/harness snapshots and conservative run limits |
| Isolated longitudinal runner | [#7](https://github.com/AndrewGodlewsky/code-comments/issues/7) | #5; tested isolation, fresh sessions, cumulative code, grading and complete trace/cost records |
| Diverse pilot corpus | [#8](https://github.com/AndrewGodlewsky/code-comments/issues/8) | #5; pinned, licensed, independently reviewed tasks and leakage boundaries |
| Placement pilot | [#9](https://github.com/AndrewGodlewsky/code-comments/issues/9) | #6–#8; actual model outcomes, uncertainty, costs and a proceed/narrow/revise decision |
| Hill-climbable skill evals ([plan](evaluation/skill-evals.md)) | [#22](https://github.com/AndrewGodlewsky/code-comments/issues/22) | Offline harness #15 and draft cases #16 first; judge #17, live adapter #18 and downstream confirmation #19 wait on #6/#7/#10 |
| Skill from research: ledger, spec, variants, tournament, climb ([plan](skill/README.md)) | [#28](https://github.com/AndrewGodlewsky/code-comments/issues/28) | User chose (2026-11-07) to build variants in parallel with #9; ledger #23, spec #24 and variants #25 offline; tournament #26 needs #18/#6 |
| Canonical writer/maintainer skill | [#10](https://github.com/AndrewGodlewsky/code-comments/issues/10) | #9; generated context measured against reference and external-writer baselines |
| Held-out confirmation and model economics | [#11](https://github.com/AndrewGodlewsky/code-comments/issues/11) | #10; powered frozen design, separate budget, independent replication and bounded claims |
| Four-client distribution and release | [#12](https://github.com/AndrewGodlewsky/code-comments/issues/12) | #10–#11; license, downloadable versioned artifacts and real installation/invocation checks |

The runner and corpus can proceed independently after the first foundation. A
budget decision does not block offline development; it blocks paid execution.
Future work must record its branch before editing. Do not keep the first branch
open for the whole roadmap, and do not close the parent when its first child closes.

## Decisions and boundaries

The [evaluation protocol](research/evaluation-protocol.md) remains the canonical
experimental proposal. Model tiers, budget, corpus size, meaningful effect and
noninferiority margins, activation policy and distribution license are not settled
by opening these issues. User authorization in this task covers planning and
starting implementation; it is not a paid campaign budget or an accepted efficacy
threshold. The user explicitly chose **offline work only** on 2026-11-05; #6
remains pending until that direction changes. The first engineering choice is Python 3.12+ standard library for an
offline diagnostic, not a constraint on the final skill's supported languages.

First validate a small executable boundary before building orchestration. Use
existing benchmark machinery where an artifact audit supports it. A toy fixture
does not replace the diverse corpus or provide statistical evidence. CI and
automated regression checks grow with the runnable artifacts in #7 and #12.

Positive results are not a completion requirement we can manufacture. Publish
null/negative findings, narrow claims, and resolve a material product pivot with
the user. The parent closes after the intended deliverable and evidence gates are
satisfied, or after an explicitly agreed revised outcome—not because tickets ran out.
