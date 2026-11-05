# Research protocol: comments as persistent context for coding agents

Status: proposed research design, not an approved benchmark or implemented skill.
Expanded 2026-11-05 after the user's request for deep benchmarks. No model trials
have been run in this repository. The goal is to establish or reject specific
claims, with uncertainty, rather than design a benchmark guaranteed to confirm
the initial intuition. Corpus choices, budgets, and release thresholds below are
proposals to settle before confirmatory runs.

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

The baseline omits the added experimental fact inventory, not every comment in a
repository. Preserve license headers, compiler/linter directives, type annotations,
and other operational comments across arms. Docstrings can affect runtime
introspection and doctests: treating their removal as automatically semantics-free
would confound the experiment. Validate equivalent baseline behavior and account
for any treatment-visible test or line-number differences before using a fixture.

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

Score each task as **correct maintenance without breaking previously required
behavior**, judged by independent acceptance checks. For the main roll-forward
study, use strict completion of whole sequences as the primary endpoint, defined
below; per-task success can hide cumulative harm. Controlled-transition studies
can use task success as their separately declared primary endpoint.

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

## Operational definition of a successful sequence

For the main roll-forward study, define success before running agents:

1. Each step implements its visible request within the same fixed resource policy.
2. Each step passes independently maintained acceptance checks and all still-valid
   prior behavioral requirements. A requirement deliberately superseded by the
   next request is retired explicitly in evaluator metadata, not by the agent.
3. The agent does not weaken the evaluator, access forbidden future solutions,
   or require unbudgeted human rescue.

All steps must pass for a sequence to count as strict success. Report time to first
failure and per-step results alongside this endpoint. If a failed sequence stops,
its strict outcome is failure; later unattempted steps are not observations of
individual task failures. Predeclare whether a separate diagnostic run continues
after failure or uses a recorded repair. Keep repaired runs out of unassisted
success counts and include their costs in any assisted-workflow result.

For context maintenance, annotate a private fact ledger with each fact's evidence,
scope, owner, introduction time, and validity interval. At each transition, score
supported retained facts, missed updates, obsolete claims, contradictions, and
unsupported new explanations. The denominator is the required fact/update set,
not total comment count. Report precision of asserted claims and recall of required
context separately; otherwise an agent can win by deleting all explanation.
Allow legitimate relocation or paraphrase and count each underlying fact once.

Use executable outcomes for behavioral correctness. Supplement them with blinded
human assessment of rationale support and a calibrated rubric for facts that
tests cannot adjudicate. A model judge can assist, but must not be the sole judge
of its own model's claims. Record disagreements and adjudication. This follows the
distinction between outcome and transcript grading in Anthropic's engineering
guide; it is a proposed design, not an experimentally validated rubric here.
[Guide, grader types and coding-agent evaluation](https://www.anthropic.com/research/demystifying-evals-for-ai-agents)

## Sampling, uncertainty, and what "significantly better" means

An apparent improvement can come from run randomness or an unusually favorable
set of repositories. Bjarnason, Silva, and Monperrus observed 2.2-6.0 percentage-point
differences between single-run benchmark scores in a 60,000-trajectory study,
including variation at temperature zero. Their configurations and benchmark are
not our target population; the result motivates replication rather than a
universal noise allowance. [*On Randomness in Agentic Evals*, v1, sections 2-3](https://arxiv.org/html/2602.07150v1)

Zhou et al. distinguish uncertainty over repeated generations on fixed problems
from uncertainty about new problems. In their 99-problem, 16-model study, repeating
the same problems cannot eliminate the latter. Their numerical ceilings are
specific to that benchmark. This motivates spending a pilot budget on both task
diversity and repetitions. [*How Much Can Repeated Running Buy?*, v2, sections 3-5](https://arxiv.org/html/2606.00920v2)

Use the following analysis plan as a starting proposal:

- **Population and unit:** name the target repository/task families, languages,
  horizons, model snapshots, and harness. A complete trajectory is an observation;
  repositories containing related trajectories are the highest sampling cluster.
  Repeated attempts, steps, and tests are not independent new repositories.
- **Paired comparison:** run the same scenario families under all conditions with
  isolated state. Average repeated outcomes within each condition and scenario;
  compare matched conditions, preserving repository clusters and equal weighting
  as specified before the study. Block/randomize execution order to reduce time,
  service-version, and cache effects. Sharing a numeric seed does not guarantee
  identical random paths after prompts diverge.
- **Primary contrast:** for a preselected reader model/harness, compare strict
  sequence success for inline versus equivalent external context. Report the
  difference in percentage points and its confidence interval. Code-only versus
  context estimates information value as a separate contrast. If the external
  condition wins, report it as a result, not a failed benchmark.
- **Intervals and inference:** use a paired repository-cluster bootstrap or a
  prespecified hierarchical analysis that retains repeated trajectories and
  arm pairing. Validate its coverage with simulated pilot-like clustered data
  before relying on it. With very few repositories, report descriptive pilot
  results and uncertainty limits rather than precise generalization claims.
  State whether inference concerns this fixed benchmark or new repositories.
- **Multiplicity:** predeclare the primary comparison and a small family of
  confirmatory secondary claims. Use a stated familywise procedure such as Holm
  adjustment, or a predeclared testing hierarchy. Treat taxonomy/model subgroup
  exploration as exploratory, especially after inspecting outcomes.
- **Power:** estimate within-scenario variance, paired discordance, repository
  heterogeneity, trajectory attrition, and costs in the pilot. Simulate power for
  the full clustered design over plausible effects and choose the number of
  repositories and repeats before confirmatory data collection. Do not plug the
  number of individual test assertions into an independent-binomial calculation.

These are our proposed methods; they are not claims that the cited papers validate
this exact longitudinal design. A statistical improvement and a useful improvement
are different thresholds. For example, a proposed practical minimum might be
**5 percentage points more strict sequence success**. A confidence interval wholly
above zero supports a directional benefit; wholly above that minimum supports the
stronger practical claim. These illustrative numbers are not accepted release
criteria. Choose the margin based on failure impact and costs before seeing the
confirmatory results. An interval crossing zero is inconclusive, not proof of
equivalence or proof that comments have no value.

For the weaker-model substitution claim, predeclare a separate noninferiority
margin against a stronger model using the best justified comparison workflow.
For example, a proposed margin of 3 percentage points would require the interval's
lower bound for weak-plus-skill minus strong-baseline to exceed -3 points, along
with a prespecified cost advantage and acceptable critical-failure rate. An
ordinary nonsignificant difference cannot establish noninferiority. Also run
strong-plus-skill when feasible so improvements available to both tiers are visible.

Report first-attempt performance and all-attempt reliability, not just the best
of several tries. `pass@k` measures at-least-one success; `pass^k` measures all-k
successes on repeated attempts, not survival across k dependent maintenance steps.
Estimate whole-sequence reliability from actual trajectories rather than raising
an average step pass rate to a power. [Bjarnason et al., section 2.3](https://arxiv.org/html/2602.07150v1#S2.SS3)

## Concrete staged pilot proposal

The [benchmark landscape](benchmark-landscape.md) supplies candidate artifacts;
this protocol owns experimental choices. Adopt a versioned subset only after
checking task rights, reproducible installation, hidden-test separation, and
whether the task genuinely needs knowledge not recoverable from local syntax.

| Stage | Proposed scope | What it decides |
| --- | --- | --- |
| Fixture audit | Independently review facts, baseline behavior, hidden checks, and task exposure; run known-correct and deliberately wrong patches | Whether the experiment can detect real constraint violations and reject evaluator tampering |
| Smoke run | 3 sequences x 3 edits x 3 conditions x 1 model x 1 repeat = 27 edit sessions | Whether state isolation, logging, grading, and fresh-session resets work; no efficacy claim |
| Placement pilot | 12 independent scenario sequences, preferably from distinct repositories, x 5 edits x 3 conditions x 2 model tiers x 3 repeats = 1,080 edit sessions | Variance, retrieval failure modes, plausible effect/cost, and confirmatory sample size; no conclusive significance claim |
| Authoring/maintenance pilot | Compare verified reference context with generated context under equal evidence; use both oracle-updated and agent-maintained arms | Whether an implementable skill can create and sustain the context that helped |
| Held-out confirmation | New repository families and tasks, frozen design and powered sample, followed by a second harness/language replication | Which narrow claims reproduce outside the development set |
| Field validation | Consented real project histories over longer calendar time, with recorded interventions and human effort | Whether laboratory gains survive actual development and team use |

These counts are planning examples, not a claim that 12 sequences suffice for
statistical power. The larger pilot entails 216 complete trajectories before
writer runs, reruns, or human review. Price a smoke run and extrapolate all-in costs
before committing to a paid campaign. No model API campaign or corpus installation
has been performed as part of the literature review.

Candidate scenario families should include a non-obvious ordering requirement,
domain representation distinction, cross-file contract, compatibility workaround
whose removal becomes valid later, and a genuinely obsolete constraint. Include
straightforward changes where added explanation should provide little benefit.
Stratify results by knowledge type and locality; do not select only fixtures that
were chosen because comments already helped the model under test.

## Prevent knowledge leakage and unfair baselines

For every exposed fact, record the source and earliest time it was knowable. A
writer may use contemporaneous requirements, tests, callers, and recorded design
decisions available to both arms. It may not see future bug fixes, later requests,
hidden tests, benchmark answer patches, or the evaluator's private fact ledger.
Keep oracle-written reference context labeled as a feasibility upper bound.

Check Git history, remotes, neighboring files, issue links, caches, global agent
memory, inherited instructions, and network access for alternate answer channels.
Use isolated evaluation workspaces with equal access policy; research notes and
this repository's coordination records are not agent-visible experimental facts.
Keep normal visible tests and discovery pointers equivalent across arms. Log which
facts were actually returned by tools and retained after truncation/compaction.
Present-but-unread context cannot explain a demonstrated information-use mechanism.

Retain both controlled-exposure and natural-discovery experiments. In the former,
provide matched facts directly to isolate use; in the latter, allow ordinary search
under matched limits to test discoverability. The physical location can affect
retrieval, context length, and cache reuse: measure those mechanisms instead of
asserting they are automatically controlled by equal word counts.

For the product comparison, use an equally capable external-document writer with
the same evidence and maintenance budget. For a smaller diagnostic study, use
human-reviewed equivalent wording in both locations. An external arm should have
useful structure and navigation; a hybrid arm may be the best practical outcome.
Keep executable tests/specifications as a serious alternative for facts that can
be enforced, not just explained. Comments supplement those checks in every arm.

Treat stale, irrelevant, and deliberately conflicting context as separate
robustness conditions. Label them explicitly; do not silently contaminate the main
accurate-information comparison. Include migrations where the correct action is
to change or delete a formerly valid explanation rather than obey it forever.

## Cost ledger, artifacts, and decision gates

Track input/output/cache tokens, model versions and prices at run time, tool and
container costs, wall time, writer/reviewer passes, retries, repairs, and measured
human minutes. Report tokens and time alongside money so pricing changes do not
erase the finding. Count failed runs in total costs. Cost per successful sequence
is total treatment cost divided by successful sequences; if none succeed, report
that the ratio is undefined rather than hiding the failures. Separate research
corpus-construction expense from deployment cost, and show amortization assumptions
for reusable comments across project horizons.

Ariño de la Rubia and Pafka's intensive study used one machine-learning engineering
task across 584 runs. Agent/model pairing, compliance, and prompt caching changed
the interpretation of quality and cost. Its one-task setting cannot establish
general coding superiority; it reinforces logging these factors rather than
equating model price with workflow cost. [*Identical Runs, Different Results*, v1,
sections 3-5](https://arxiv.org/html/2609.33812v1)

The minimum reproducibility bundle is a pinned manifest of repository and task
versions, rights/provenance, model/harness/prompt settings, treatment preparation,
fact equivalence audit, hidden evaluator version, declared analysis, run IDs and
randomization, sanitized raw traces/tool outputs, resulting patches, per-step
scores, resource ledger, exclusions, and analysis scripts. Store hidden artifacts
separately from agent-visible data; release them only under a planned test-set
rotation policy. Failed and timed-out agent runs remain outcomes; independently
verified infrastructure failures follow a prespecified rerun/exclusion rule.

| Observation | Supported next decision |
| --- | --- |
| Verified context helps, but inline and external placement are comparable | Pursue knowledge quality/retrieval; do not market inline superiority |
| Inline helps on selected fact categories only | Narrow the skill and state its replacement boundary |
| Ideal comments help but generated/maintained ones fail | Improve writer provenance and maintenance before claiming product efficacy |
| A weaker model improves but remains worse or more costly overall | Report an improvement, not model substitution or savings |
| Gains disappear under hidden regression checks or held-out tasks | Revisit validity/generalization; do not ship an unsupported benchmark claim |
| Maintained inline context improves sequence success beyond the chosen margin and meets cost/robustness gates | Make the limited claim for tested models, tasks, horizons and harnesses; replicate before broadening |

An attractive comment score, single best run, or higher public leaderboard number
cannot substitute for these outcomes. Keep the intent's open hypotheses intact
until a recorded experiment supplies the required evidence.

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
