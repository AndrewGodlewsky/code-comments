# Research protocol: comments as persistent context for coding agents

Status: proposed research design, not an approved benchmark or implemented skill.
The research question was clarified by the user on 2026-11-04. No model trials
have been run in this repository.

## The question to answer

Can selected knowledge stored in code comments replace some separate project
documentation and help less capable coding models make more correct, consistent
changes over successive development sessions?

The target is sustained maintenance performance, not the number of comments,
the attractiveness of generated prose, or a single code-generation example.
The product workflow remains undecided until evidence informs it.

## Separate the hypotheses

| Hypothesis | Comparison needed | Evidence against it |
| --- | --- | --- |
| Additional contextual knowledge helps | Code/tests alone versus the same code/tests plus verified context | No meaningful improvement, or added context causes regressions |
| Location matters | Identical contextual facts inline versus in accessible external docs | External docs match or outperform inline comments |
| Some docs can be replaced | Inline-only versus external-only and, later, hybrid, for explicitly selected facts | Required knowledge becomes hard to find or crosses too many ownership locations |
| Less capable models benefit | Matched trials across empirically characterized model tiers | Gains occur only in the stronger model or do not close the performance gap |
| Benefits survive project evolution | Repeated changes across fresh sessions | Stale statements, duplicated explanations, or maintenance overhead accumulate |
| A skill can produce the helpful context | Generated context versus human-reviewed reference context | Ideal comments help, but the skill cannot produce or maintain them reliably |

Comments may help without outperforming documents. A strong model may write
useful comments without making a less capable model reliable. These are distinct
outcomes and should lead to different product decisions.

## Phase 1: test placement before testing an authoring skill

Construct a small set of realistic repositories with known behavior, tests, and
requirements. For each scenario, write a reviewed inventory of contextual facts:
business constraints, rationale supplied by the scenario's author, invariants,
non-obvious relationships, compatibility constraints, and scope of ownership.
Assign stable fact identifiers in evaluation metadata, not mandatory production
comment tags.

Prepare independently versioned conditions from the same code baseline:

1. **Code and tests:** no added rationale inventory exposed to the agent. This
   measures the value of supplying information; it is not a fair test of location.
2. **Inline:** expose the inventory as comments beside its owning code.
3. **External:** expose the same facts in well-organized, linked project documents.
   Give the agent a normal discovery pointer and working search/read tools.
4. **Hybrid, if warranted:** divide facts by ownership, with each fact stored once.
   Compare this when testing replacement boundaries, rather than expanding every
   pilot into a large factorial study immediately.

Use equivalent facts and comparable wording in inline and external conditions.
Review this equivalence independently: a better explanation in one arm would
confound explanation quality with placement. Existing executable tests, code
structure, tool access, and task instructions should otherwise match.

Do not handicap the external-doc condition by hiding the files, disabling search,
using vague document names, or giving it outdated material while giving the
inline condition perfect material.

## Phase 2: test the writer and maintainer

Only after establishing whether placement helps, evaluate an actual Code Comments
skill. Give the writer the same evidence available to the documentation writer.
Separate two experiments:

- **Oracle-updated context:** a human-reviewed update keeps each condition's facts
  correct. This isolates the reader's ability to discover and use the knowledge.
- **Agent-maintained context:** the coding agent must update its condition's
  comments or documents during the task. This measures end-to-end maintenance,
  including drift and unsupported rationale.

An optional stronger-model authoring pass is a separate treatment. Account for
its cost; do not attribute its knowledge or quality entirely to comment placement.

The expected output may be adding, keeping, revising, relocating, or deleting
explanation. It may also be no change. A writer that adds plausible explanations
without evidence should fail the relevant checks even if the code still runs.

## Long-running task sequences

Use realistic sequences whose later changes depend on earlier constraints. For
example: introduce idempotency, add retries, change a storage contract, migrate a
producer/consumer pair, and remove a compatibility workaround. These are candidate
scenario families, not selected implementation requirements.

Use fresh agent sessions between edits in the main persistent-context experiment.
Persist repository state; withhold the earlier conversation. This asks whether
knowledge survives in project artifacts. A separate long-context or compacted-chat
condition can test conversational memory without conflating it with repository
memory. Record exactly what context each session receives.

Run two styles of sequence where the budget permits:

- **Controlled transitions:** each task starts from a known correct checkpoint,
  so one early bug does not dominate all later comparisons.
- **Roll-forward maintenance:** each accepted output becomes the next input. This
  measures accumulation of mistakes, stale claims, and recovery costs. Define
  acceptance, rescue, and stop rules in advance; report failed sequences rather
  than silently repairing or dropping them.

Neither style substitutes for the other. Short experiments cannot establish
reliability over months of real development; a later field trial is still needed.

## Controls that keep the comparison honest

- Choose model tiers using documented model identities and observed baseline task
  performance. Parameter count, price, or a marketing label alone does not define
  coding capability. Pin versions when possible and record changes when not.
- Start in one reproducible harness with equal tool access. Verify distribution
  across Orca, Codex, Claude Code, and Copilot separately; then test whether useful
  effects transfer across harnesses. A skill-loading failure is not evidence that
  comments fail to help a model that actually reads them.
- Record all system/repository instructions, enabled skills, context limits,
  sampling settings, token budgets, tool behavior, and timeouts.
- Separate a controlled exposure test (both groups see equivalent facts) from a
  natural retrieval test (facts must be found under equal resource limits).
  The latter tests a possible practical advantage of co-location.
- Keep evaluation requirements and hidden tests outside the agent's visible
  workspace. The agent may use normal project tests; those must be the same in
  each comparison arm. Tests and reviewer criteria should be authored independently
  of the skill's preferred wording.
- Use multiple independent runs, paired scenarios, randomized execution order,
  and reviewers blinded to the treatment where practical. Preserve unsuccessful
  runs and record reasons for exclusions.
- Pilot to estimate variance and cost, then fix the confirmatory sample size,
  primary metric, practical effect threshold, and analysis before looking at the
  confirmatory results. Keep held-out scenarios for that stage.

## Outcomes and costs

The primary outcome should be a **correct maintenance task without breaking
previously required behavior**, judged by independent acceptance checks. Also
report completion of whole sequences; per-task success can hide cumulative harm.

Secondary outcomes:

- Regression rate and violation of known invariants.
- Supported, stale, contradictory, missing, and duplicated contextual claims.
- Success variation across repeated runs, task families, and model tiers.
- Relevant files found and useful context actually read, not merely present.
- Token use, tool calls, wall time, and paid model cost, including authoring,
  maintaining comments/docs, retries, and human rescue where measured.
- Code or behavior changed unexpectedly by a comment-only operation.
- Unnecessary diff churn and whether a second pass leaves good comments stable.

Report per-scenario results, distributions, and uncertainty, not just a pooled
average or selected screenshots. Repeated edits within one project share context
and failure modes; treat the sequence as a grouping unit when analyzing results.

For a claim about saving money, compare total cost per successful task and per
successful sequence against a stronger-model baseline. A cheaper model with many
failed retries may not be the cheaper workflow.

## Which documents might be replaceable?

Test document categories separately. Candidate replaceable facts are narrow,
code-owned rationale and constraints. A cross-cutting concept may belong beside a
shared interface, but that is a hypothesis about ownership and retrieval.

Installation instructions, research evidence, product decisions, system-wide
navigation, and historical trade-offs serve different jobs. Do not demand that
all of them move into source comments. Evaluate replacement of an explicit fact
set while keeping unrelated onboarding and operational documentation constant.

The research reports in this repository are evidence for designing a skill;
they are not duplicate explanations of an existing application implementation.

## Repository artifacts to add when the experiment is agreed

- A versioned corpus with provenance and explicit redistribution rights.
- Scenario manifests, visible requirements, and a separate hidden evaluator.
- A reproducible runner and recorded environment/tool versions.
- Raw run records, compact result tables, and an analysis that can be rerun.
- Mechanical validation and CI for manifests, links, packaging, and checks.
- Release evidence separating successful installation, correct invocation,
  comment quality, and demonstrated maintenance outcomes.

Avoid filling empty instruction files with speculative policy. Add navigation
pointers as real artifacts exist, and convert repeated mechanical mistakes into
checks. Decide workflow, language coverage, and release claims after the evidence.
