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

On 2026-11-11 (#50), four candidate skills beside the hygiene skill were researched,
built and evaluated in the [incubator](../../incubator/README.md). None reliably beat a
one-line reminder sentence on graded checks. The section on
[incubator evaluations](#incubator-evaluations-and-their-lessons-50) says where those
results live and which evaluation lessons a later study should reuse.

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
- Whether a skill next to the hygiene skill adds anything over a one-sentence reminder.
  - First evidence: the four [incubator](../../incubator/README.md) evals (#50). None of
    the four skills reliably beat its reminder on graded checks, on Haiku or Sonnet.
  - Its limit: the fixtures were small and built by agents, with 2 or 3 runs per cell.
    The result is no evidence of a difference, not evidence that the two are equal.
- Whether readers miss context that lives in other files, which is
  [ADR 0001](../adr/0001-context-lives-inline-no-central-index.md)'s revisit condition.
  - constraint-sweep's fixtures (12 to 16 files) gave no evidence either way. The bare
    model passed every core check (35 of 35), so there was no miss to fix. Discovery
    itself was not measured. The pointer-comment twin could not show an effect, because
    its base case was at ceiling too.
  - Its README had said before the runs that a null result would be the revisit trigger.
    After the runs that was read against the ADR's two-part condition and not applied,
    because no miss occurred.
  - So there is no evidence for the revisit condition, and none against it in larger
    repositories. The ADR stands unchanged.

## Incubator evaluations and their lessons (#50)

Each candidate skill's folder in [`incubator/`](../../incubator/README.md) owns its result:
- `README.md`: status, results, limits and next steps.
- `research.md`: sources and the first design, kept as a dated record.
- `eval/`:
  - `CASES.md`: case design;
  - `GATE.md`: case selection;
  - `CHANGES.md`: skill edits;
  - `RESULTS.md` and `ANALYSIS.md`: tables and reasoning;
  - `HELD-OUT.md`, where a skill has one: held-out case design;
  - `iterations/`: the run records, with `benchmark.json`, each run's `grading.json`,
    and `overrides.json` where a ruling was made.

The incubator README has a cross-skill table.
`python incubator/harness.py summary <skill> <iterations>` reproduces each skill's own
table. The [planning-research overview](../planning-research-2026-11-11.html) sets out
what the results mean and which decisions they leave to the user.
[`incubator/ideation/`](../../incubator/ideation/README.md) records how the four were
chosen.

These lessons are for a later skill eval to reuse. Each lesson starts from a problem
observed in these evals, at 2 or 3 runs per cell. The remedies are proposals, untested
here:
- **Run a reminder arm. Proposal (untested): gate cases on it as well as on the bare
  model.**
  - Over iteration 1 and the held-out pairs (140 runs per arm), the reminder accounts for
    53 of the skills' 59 extra full-marks runs over the bare model.
  - The gates ran the bare arm only. So they chose cases where the bare model falls
    short, not cases that separate a skill from a good sentence.
  - A case kept because the reminder missed in the gate will tend to flatter the skill
    on that case. So the check on generalisation must be a fresh held-out pair that was
    not gated on the reminder, and that no agent who edits the skill has seen.
- **Run a shipped-skill arm.**
  - It was the only arm to fail hidden tests: 111 of 120 runs passed, against 120 of 120
    in every other arm. Six runs broke a constraint stated elsewhere, and three built only
    part of the requested change. That comparison was chosen after reading the runs, and
    its cause is a hypothesis.
  - It also tests whether a candidate is a new skill or a plugin enhancement, as
    change-drift-sweep's README stated before its runs.
- **Report each check focus, and say which count you report.**
  - Every guided arm's gain over the bare model was on prose, reply, preservation and
    restraint checks. On hidden behavioural tests, the bare, reminder and skill arms
    each passed in 120 of 120 runs.
  - Label which count you report. The incubator's
    [Running an eval](../../incubator/README.md#running-an-eval) explains how a benchmark
    headline differs from pooled n/N.
- **Run each held-out pair once, and treat it as spent.** The incubator's
  [rules](../../incubator/README.md#rules-for-every-skill-here) say how held-out cases are
  kept. Each skill ran its pair in all four arms once, after its last edit; the bare gate
  had already run it. Two fold-docs-inline held-out Haiku runs were excluded for a guard
  fault and re-run.
  - Exposure happened in every build, so no held-out pair is a blind test of v1's rules.
    It guards the v2 revision against overfitting, as designed. The counts come from the
    coordinator's scan of the build transcripts ([incubator](../../incubator/README.md),
    "Held-out exposure during the builds"):
    - Every v1 writer read its `eval/CASES.md`, which then described every case, the
      held-out pair included. No writer opened a held-out case file.
    - Every build fixer read and edited held-out case files and, in the same session,
      edited its skill. Tool calls naming a held-out case: verify-before-relying 6,
      fold-docs-inline 6, constraint-sweep 10, change-drift-sweep 8.
    - The v2 revisers made no tool call naming a held-out case.
    - Every held-out comparison with the reminder and the shipped skill was a tie or a
      lead that is not established, so the exposure produced no false win there. It
      weakens any reading that a skill "carried over" or "generalised".
    - change-drift-sweep's held-out `poll-interval-per-day` most likely decided a skill
      edit. That case was replaced, and held-out case design moved to `eval/HELD-OUT.md`,
      which skill writers do not read. The pointer case had already been described in
      CASES.md, so it is a restraint guard, not a clean test.
    - A directory listing printed change-drift-sweep's held-out file and grader file
      names to the v2 writer.
    - fold-docs-inline's v2 writer read GATE.md and CASES.md, which summarise its held-out
      cases.
    - Three held-out cases were hardened after the bare gate: fold-docs-inline's
      `stale-ordering-reason`, constraint-sweep's `first-wins-reason-in-caller` and
      change-drift-sweep's `poll-interval-average-wait`.
  - fold-docs-inline's reminder lead of one check on held-out Haiku (57/60 against 56/60,
    pooled) rests on one of the re-runs. With the excluded original, the reminder would
    have 55/60.
  - Proposal (untested): keep held-out cases out of CASES.md from the start; build them
    after the skill is frozen, or let no agent that saw them edit the skill; and add a
    transcript check for this to the harness.
  - A spent pair is not a second generalisation check.
- **Treat a gate as case selection, and re-gate after hardening.**
  - Gate runs were never counted.
  - No skill re-ran its gate after hardening (all four READMEs say so). In
    change-drift-sweep, the first bare measure found headroom on Haiku in two of four
    hardened training cases and on Sonnet in none.
  - constraint-sweep had no core headroom at all.
  - Until a re-gate, hardened headroom is a hypothesis.
- **Make rulings blind, and record who made them.**
  - All 37 rulings were made by auditor agents, none by a human. The run folders name the
    arm, so the rulings were not blind.
  - The hygiene eval's [README](../../evaluation/hygiene/README.md) asks for human
    rulings instead.
  - verify-before-relying's tie with the reminder in iteration 1 rests on 2 rulings that
    credited `with_skill` (and 1 that credited the reminder). Two more credited v2's
    training re-run.
  - Future rulings should use opaque run ids, and a human should review them or the
    user should accept them.
- **Write the exclusion rule for environment faults before the runs.** Here it was
  decided after the runs. The incubator's
  [guard note](../../incubator/README.md#running-an-eval) gives the runs the guard
  blocked, the instruction for run agents, and when that instruction can be dropped.
- **Size fixtures to the claim.**
  - With 5 to 16 files, every run could read every file. So no skill's search step was
    measured, and neither was change-drift-sweep's script.
  - Every skill arm was told to read its skill, so activation was not measured either.
    #20 measures it for the shipped skill.
- **State the decision rule before the runs, and size the runs by power.**
  - Three of the four READMEs said before their runs what a tie would mean, and that rule
    decided their recommendations: verify-before-relying and constraint-sweep would
    recommend the sentence, and change-drift-sweep would be a plugin enhancement if the
    shipped skill tied it. fold-docs-inline said only that a tie or a loss would be
    reported. constraint-sweep also said a null result would trigger ADR 0001's revisit.
    That rule was not applied as written (see its README).
  - A later study should also fix the primary metric, the comparison and the test in
    advance. One proposal: run-level full core, skill against reminder, with a stratified
    exact test by case.
  - Telling 95% from 85% needs about 140 runs per arm (two-sided α = 0.05, power 0.8).

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
