# Code Comments: problem, evidence, and benchmark direction

Research snapshot: 2026-11-05. Start here to review the expanded investigation.
This is a targeted primary-source review and proposed evaluation plan. We have
not implemented the skill, run the cited benchmarks, or measured its effectiveness.

## Assessment

The problem is worth testing: important constraints and reasons can disappear
between development sessions even when the code survives. The evidence supports
investigating accurate, selective context. It does **not yet establish the full
product claim** that maintained inline comments outperform equally informative
external documents, survive successive changes, and let less capable models
deliver comparable reliability at lower total cost.

We found people already addressing important parts of this problem, including
inline documentation generation, repository-native rationale skills, dependency-aware
documentation, and agent experience memory. Existing longitudinal coding benchmarks
provide useful infrastructure. The missing piece in this review is a controlled
experiment connecting **knowledge placement, ongoing maintenance, future edit
quality, and model economics**. This is a statement about the reviewed evidence,
not a claim that nobody has ever attempted it.

The recommended next step is a small, carefully controlled evaluation of verified
context before selecting the skill's authoring workflow. If comments win only for
certain facts, or external/hybrid context works as well, that is actionable evidence.

## What the problem actually contains

The user's observation combines several distinct failure modes:

| Failure | What might help | What we need to measure |
| --- | --- | --- |
| A rationale is never recorded | Capture it while the user or implementer can supply evidence | Supported facts retained; invented reasons avoided |
| A fact exists but the next agent never finds it | Placement beside relevant code, navigation, or retrieval | Fact discovery, actual exposure, and correct use |
| Code changes but its explanation does not | Joint change review and evidence-based update/removal | Stale claims per transition and cost to correct them |
| Local explanations omit a system-wide relationship | A shared contract or coherent external account | Cross-file constraint preservation and global questions |
| Context overwhelms the reader | Selectivity, pruning, and retrieval budgets | Correct changes per token/time budget |
| A cheaper model makes repeated mistakes | Better task-relevant information and an effective harness | Whole-sequence reliability and total cost versus a stronger baseline |

These are our decomposition and proposed measurements, not six established effects.
Putting text inside a source file does not make it executable truth: a comment can
still disagree with behavior. The potential advantage is that explanation is
encountered and maintained at the point of change. That advantage must be measured.

Conversely, code cannot uniquely reveal every reason for its own design. A current
implementation may show an ordering without establishing which historical failure
made that ordering necessary. Capturing the reason from contemporaneous evidence
is different from asking a model to infer a plausible story afterward. This is
consistent with the historical tensions documented in our
[Naur, Knuth, Parnas, Dijkstra, Kernighan, and Pike review](historical-comment-design.md).

There is also an alternative to manually maintaining two descriptions: generate
selected documentation views from an owned source of facts, or turn enforceable
requirements into tests/contracts. Those approaches still have scope and fidelity
limits. The product should compete with useful alternatives rather than assume
that every external document is redundant.

## What the evidence says

| Evidence family | Best supported reading | Boundary |
| --- | --- | --- |
| Direct comment interventions | Correct supplied information can improve bounded model tasks; incorrect information can harm them | Often isolated functions, solution-prefill knowledge, or oracle-derived comments |
| Human studies and historical practice | Rationale, contracts and orientation can support understanding; restraint and freshness matter | Human comprehension and expert advice do not establish agent effects |
| Comment-aware model training | Some training/decoding recipes improve code generation | Changing weights is different from adding context to a deployed agent |
| Repository instructions and memory | Available context can alter behavior and cost without a reliable accuracy gain | Delivery, retrieval and actual use must be distinguished |
| Successive-edit benchmarks | Cumulative code changes expose failures missed by isolated tasks | These benchmarks do not automatically test comments as the remedy |

For designs, effect sizes, publication status, source-internal discrepancies and
counterevidence, read the [direct evidence deep dive](comment-context-deep-dive.md).
The [earlier eight-study map](agent-context-evidence.md) remains useful background;
the new report extends its scope rather than treating it as an exhaustive review.

One especially relevant bounded result is Pan et al.'s transfer of correct comment
prefixes from stronger to weaker models. It supports an information-transfer
mechanism, but is not a test of maintained project comments or equivalent external
documents. [Study](https://arxiv.org/html/2609.09242v1)

Useful counterevidence comes from *Delivered, Not Used*: its tested memory systems
did not yield a statistically clear average resolution benefit despite additional
context and costs. This does not test inline placement; it challenges the shortcut
from "more available memory" to "better agent work."
[Study](https://arxiv.org/html/2611.01718v1)

Do not generalize either finding to every model or project. In particular, an
improvement on reference-patch exact match, documentation quality, or a helpfulness
judge is not yet fewer downstream regressions.

## Existing people and systems to learn from

The [systems and researchers report](related-systems-and-researchers.md) provides
the source trail, implementation details, evidence limits, and additional teams.
These are research leads, not endorsements or claims of product parity:

| Lead | Why it matters here |
| --- | --- |
| Oliver Zehentleitner — [Keep the Why](https://github.com/oliver-zehentleitner/keep-the-why) | Close rationale-preservation skill using repository Markdown; a useful external-context comparator |
| Meta's [DocAgent authors](https://aclanthology.org/2025.acl-demo.44/) | Inline docstring generation; separates an existing writer mechanism from our unproved downstream maintenance benefit |
| [RepoAgent](https://github.com/OpenBMB/RepoAgent) | Dependency-aware documentation updates offer a maintenance alternative worth inspecting |
| [REM authors](https://arxiv.org/abs/2610.27377) | Selection, recall and pruning of coding-agent experiences; relevant to what deserves to persist |
| [Pan and collaborators](https://arxiv.org/abs/2609.09242) | Direct investigation of what makes comments help code generation |
| [Bjarnason, Silva and Monperrus](https://arxiv.org/abs/2602.07150) | Repeated-run evaluation methodology that guards against noisy improvement claims |

Keep the Why's small published fixture is informative but should not be described
as demonstrated prevention of code breakage: its inspected result concerns
re-proposing a rejected option, and neither condition broke the tested behavior.
The detailed report links the raw result and distinguishes this from a maintenance
success benchmark.

## Which benchmarks help?

The [benchmark landscape](benchmark-landscape.md) compares task units, evaluators,
versions, artifact availability, rights, and adaptations. Start with these roles:

| Role in our study | Candidate | Main adaptation needed |
| --- | --- | --- |
| Repeated edits to an evolving implementation | SlopCodeBench | Add matched knowledge conditions and inspect quality metrics for comment-length bias |
| Dependent repository fixes across fresh sessions | ChainSWE | Add context treatments while preserving cumulative code state and fair task exposure |
| Regression-sensitive evolution | SWE-CI | Control its adaptive requirement-generation mechanism before attributing differences to placement |
| External real-repository robustness check | Version-pinned SWE-bench family tasks | Add an appropriate maintenance design; isolated issue success does not establish longevity |
| Retrieval or comment-quality diagnostics | RepoQA and documentation-specific evaluations | Use as mechanism checks, not the product's primary success metric |

These are complementary choices, not a recommendation to run every benchmark.
Artifact revisions matter: paper counts, default dataset splits, and current
repositories can differ. The landscape records those differences and licensing
uncertainties. Reusing a harness does not automatically grant rights to every
repository/task or validate its grading assumptions.

## What would justify the product claim?

The [canonical evaluation protocol](evaluation-protocol.md) contains the proposed
controls, analysis, costs and stages. Its central comparison is:

**The same initial implementation, tasks, tools, budgets and verified facts, with
the facts placed either beside their owning code or in accessible external docs.**

Code/tests without the added inventory form a separate information-value baseline.
Later, test generated comments and agent maintenance, rather than only ideal
human-reviewed explanations. Reset conversation between edits while retaining
repository state. Track removal of obsolete constraints as well as preservation
of still-valid ones. Include cross-file and ordinary low-context tasks.

"Better" should mean more complete maintenance sequences without regressions,
acceptable critical-error rates, and useful savings after authoring, review,
updates, retries and recovery. It should not mean more comments, nicer prose,
a cherry-picked successful run, or passing tests that the agent weakened.

The protocol distinguishes statistical evidence, a minimum worthwhile effect,
and weaker-model noninferiority. It proposes paired repository-aware analysis,
independent repetitions, held-out project families, and a powered confirmatory
study after the pilot. Example thresholds and run counts are explicitly proposals;
they are not results or already accepted release gates.

If ideal context helps but the skill writes unsupported or stale context, the
writer/maintainer is the limiting factor. If the weaker model improves but remains
less dependable or costs more after retries, the model-substitution claim fails.
If external or hybrid context wins, retain that evidence and reconsider placement.

## Review order and decisions still needed

1. Read this synthesis, then the direct evidence report for the strongest support
   and counterexamples.
2. Review the existing systems to decide what should be a baseline or reused
   component, rather than automatically building another writer.
3. Review the benchmark landscape and choose a small candidate subset to audit.
4. Agree the protocol's target task population, model/harness comparison, practical
   margins and affordable pilot budget before building the runner.

The product's activation policy, comment taxonomy, language coverage and client
distribution remain open. This review does not select them prematurely. A later
benchmark implementation should have its own task, reproducible artifacts and
recorded trials. For now, the deliverable is a reviewable evidence base and a
falsifiable experiment design.

## Search scope and limits

The investigation extended the repository's 2026-11-04 historical and empirical
reports through targeted web searches, primary paper reading, linked artifact
inspection, and citation following. Parallel research covered direct comment
effects, benchmark infrastructure, and existing systems; each report records its
searches and access limits. Root synthesis additionally inspected primary studies
on repeated-run uncertainty and agent-evaluation design.

This is not a registered systematic review or exhaustive patent/novelty search.
Recent preprints, publisher abstracts, project self-evaluations and peer-reviewed
papers have different evidential weight. We inspected selected historical passages,
not complete books. Published results and tool claims were not reproduced locally.
No people were contacted, paid experiments run, or external tools installed.
