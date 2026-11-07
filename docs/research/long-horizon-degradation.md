# Do coding agents tangle a codebase over many changes, and are weaker models worse?

Research date: **2026-11-07**, for issue #35 (R5). This is a targeted primary-source review, not a
systematic review. No experiment was rerun. It extends the [benchmark landscape](benchmark-landscape.md),
which covers the *setup* of SlopCodeBench, ChainSWE and SWE-CI, and the
[coding-agent evidence map](agent-context-evidence.md) §§7–8, which gives ChainSWE and SWE-CI headline
results. Those are cited, not repeated. "pp" means percentage points. Evidence types: **measured**
(experiment or repository mining with a stated method), **survey**, **practitioner report**, **vendor
claim**. Every source is an arXiv preprint unless a venue is named.

Written to be read as evidence for a decision, so it says plainly where the evidence stops.

## 1. Question and bottom line

The user's experience: weaker (Haiku-class) models write a fine single feature, but over many features
the codebase becomes "a tangled mess". The hope is that inline comments would prevent this.

**Degradation over successive agent edits is measured and real.** On SlopCodeBench, structural erosion
rises in 77% of agent trajectories and grows about 5× faster per step than in human repositories, while
pass rates fall. Building on agent-written code lowers the next agent's success by up to 13 pp. In a
causal study of 806 open-source projects, adopting Cursor persistently raised static-analysis warnings
by about 30% and code complexity by about 41%.

**That weaker models degrade *more* is not supported.** No study reports degradation rates by
model tier, and the indirect evidence points the other way: frontier models (Claude Opus 4.7 included)
erode code as much as open models, and GPT-5.4-nano held up under carried-forward state as well as
GPT-5.5. Weaker models fail more often outright, which is a different thing.

**No study tests comments or documentation against long-horizon degradation.** The closest analogue,
quality instructions in the prompt, lowers the starting level of mess by roughly a third but does not
slow the rate at which it accumulates. Overall strength: **strong** that degradation happens, **weak and
mostly negative** on the model-tier claim, **absent** on comments as the remedy.

## 2. Findings

### 2.1 Quality degrades over successive edits (measured)

- **SlopCodeBench** ([Orlanski et al., v2, 2026-05-07](https://arxiv.org/html/2603.24755v2); NeurIPS 2026
  poster). Agents extend their own code through 36 problems and 196 checkpoints. Two metrics:
  *erosion* (share of complexity mass in functions with cyclomatic complexity above 10) and *verbosity*
  (lint-flagged plus clone lines per line of code). Erosion rises in 77% of trajectories and verbosity
  in 75.5%. Functions with complexity of at least 10 rise from 3.6 to 23.7 on average. Structural
  duplication grows 96%. Core pass rate falls from 64.6% early to 35.5% late, and cost per checkpoint
  rises 2.2×. Against a panel of 473 human Python repositories, agent code ends 2.3× more verbose and
  2.0× more eroded. Per checkpoint, agent erosion grows about 5× faster than the human median and
  verbosity about 6.6× faster. **Measured.** The best agent strictly solves 14.8% of checkpoints, so
  every model here is struggling.
- **Building on agent code** ([Patel et al., "Is Agent Code Less Maintainable Than Human Code?",
  2606.21804v1, 2026-06-19](https://arxiv.org/html/2606.21804v1)). Two-step chains over 1,377 instances
  with four models. The same model resolves the second task less often when the first step was written
  by an agent rather than a human. The largest drop is 13.1 pp (GLM 4.7 on SWE-Bench Pro, 45.2% to
  32.0%). In 4 of the model-benchmark cells the agent-built base did as well or better (e.g. Claude
  Sonnet 4.5 on FeatBench, +6.2). Drops are largest for refactoring tasks (−8.2 pp mean). **Measured;**
  one run per pair. The paper's prose claims drops of "around 33-88%" that its own Table 2 does not
  support.
- **Carried-forward state** (ChainSWE, [Jin et al., v2, 2026-09-01](https://arxiv.org/html/2607.02606v2)).
  About half (48%) of later-position failures are *chain errors*: tasks that pass when earlier gold fixes
  are applied but fail on the agent's own earlier patches. The share rises from 43% at position 2 to 52%
  at position 3. **Measured;** tests only, with no structural metrics.
- **SWE-CI** ([Chen et al., v4, 2026-04-01](https://arxiv.org/html/2603.03823v4)). Regression rate rises
  with iteration count for 12 of 20 models. All 20 models score below human code on the maintainability
  index, although 15 beat it on Pylint. **Measured.**
- **SWE-Chain** ([NeurIPS 2026 poster, 2605.14415](https://neurips.cc/virtual/2026/poster/139028)).
  Chained package upgrades where each step starts from the agent's own code. The mean is 44.8% of
  requirements resolved across nine setups, and the authors call agents "brittle". **Measured;** I
  verified the abstract only, not any per-step slope.

### 2.2 Weaker versus stronger models

No source reports per-model degradation *slopes* or tests the user's tier claim directly. What exists:

- **SlopCodeBench final-snapshot quality does not separate by tier.** Final erosion ranges from 0.49
  (GPT 5.5) to 0.76, and the worst includes **Claude Opus 4.7** (0.76) alongside Kimi K2.6. MiniMax M2.7
  solves only 2.0% of checkpoints yet has erosion (0.73) similar to the top models
  ([v2, Table 1/8](https://arxiv.org/html/2603.24755v2)). The two strongest solvers (GPT 5.5 and 5.4)
  do have the cleanest code, so capability and quality are not unrelated. But the worst code is not
  confined to weak models.
- **ChainSWE relative drop is similar across tiers.** Going from oracle state to the agent's own state
  costs about 29% of per-bug accuracy for GPT-5.5, 30–33% for GPT-5.4-mini, GPT-5.4-nano, Opus 4.5 and
  DeepSeek-V4-Pro, 37% for Opus 4.7 and 41% for Gemini 3.1 Pro (my arithmetic from Table 2). In absolute
  terms, **GPT-5.4-nano (45.1%) beats Claude Opus 4.7 (40.5%)** in the sequential mode. The authors write
  that "strong single-shot ability does not guarantee robustness to self-generated state". **Measured;**
  chains average three bugs.
- **Patel et al.** GLM 4.7 shows the largest and most consistent drop. The design cannot separate a bad
  builder from a bad maintainer, because the same model writes both steps.
- **SWE-CI.** Only the two Claude Opus models exceed a 0.5 zero-regression rate; most models are below
  0.25, and weaker models exhaust the 20-turn budget. This is the one result where stronger models are
  clearly better at *not breaking things over iterations* ([v4](https://arxiv.org/html/2603.03823v4)).
  Per-model values appear only in figures.
- **Single-shot smell studies point both ways.** Larger models produced *more* Long Method smells
  (Qwen-Coder 480B: 11; human baseline: 1), partly because small models failed before writing enough code
  to trigger them ([Zhu, Tsantalis, Rigby, 2605.02741v1](https://arxiv.org/html/2605.02741v1)). Sonar's
  Java study found Claude Sonnet 4 the most verbose and OpenCoder-8B the highest in issue density
  ([vendor report, 2025-08](https://www.sonarsource.com/the-coding-personalities-of-leading-llms)).

**No study included a Haiku-class Anthropic model in a long-horizon quality measurement.** The closest
small-model data is GPT-5.4-mini and GPT-5.4-nano in ChainSWE, and it does not support the claim.

### 2.3 Reported mechanisms

| Mechanism the user suspects | What is measured | Source |
| --- | --- | --- |
| Local patches instead of restructuring | Agents grow one function instead of refactoring. Opus 4.7's `main()` went from complexity 13 to 92 and from 38 to 240 lines over 8 checkpoints. Seven identical flag handlers had no shared helper. | SlopCodeBench v2, App. B |
| Smaller patches that skip structural work | LLM patches are consistently smaller than human patches | SWE-CI v4, Obs. 6 |
| Duplicating instead of reusing | Structural duplication +96% across checkpoints. Agents cite duplication as a refactoring motive in 1.1% of refactoring commits, versus 13.7% for humans. | SlopCodeBench; [Horikawa et al., 2511.04824v1](https://arxiv.org/html/2511.04824v1) |
| Silent contract changes | Changed input validation or error handling in the first step predicted later failure (OR 1.83). The change survived into step 2 in 85.9% of judged cases but directly caused the failure in only 20.6%. | Patel et al. |
| Edits in the wrong place, or incomplete | Earlier patches overshoot (edit unrelated files) or undershoot (omit parts of a multi-file fix), about 1:9 | ChainSWE |
| Growth tracks volume | Architectural smells correlate with lines of code (ρ = 0.94). Development stage had no effect once volume is known. | Zhu et al. |

What did *not* predict downstream failure: static complexity metrics of the first step (Patel et al.).
Low-level agent refactoring left smell counts essentially unchanged (Horikawa et al.).

### 2.4 Interventions and effect sizes

- **Quality prompts (closest analogue to standing guidance).** An "anti-slop" prompt cut initial
  verbosity by 28–36% and erosion by 34–58% on three GPT models. A plan-first prompt cut erosion by 0.10
  to 0.21 absolute. Both cost correctness: strict solve rate fell 2.4 and 3.6 pp, and cost rose about
  12%. **Degradation continued at about 1.3 quality points per checkpoint.** Only one model improved
  from start to end ([SlopCodeBench v2 §3.4](https://arxiv.org/html/2603.24755v2)). The abstract says
  "up to a third"; §3.4 reports up to 62% for erosion. **Measured;** three models plus one MiniMax run.
- **Test context, not test instructions.** On SWE-bench Verified with small local Qwen models, a
  test-driven development *prompt* raised test-level regressions from 6.08% to 9.94%. Giving the agent a
  map from code to its tests lowered them to 1.82%, a 70% reduction. Resolution changed little in
  phase 1 (31% to 29%) and rose from 6/25 to 8/25 in phase 2
  ([Alonso, TDAD, 2603.17973v1](https://arxiv.org/html/2603.17973v1)). **Measured;** single author,
  100 and 25 instances, no significance tests, weaker models only. It is relevant because it is *context*
  that helped and *instruction* that hurt.
- **Linter feedback loops.** Iterating GPT-4o against Bandit and Pylint for up to ten rounds cut
  readability violations from over 80% of samples to 11% and reliability warnings from over 50% to 11%
  ([Blyth et al., 2508.14419v1](https://arxiv.org/abs/2508.14419v1)). **Measured;** single-shot snippets,
  not a long horizon.
- **Agent refactoring passes.** In the wild, agent refactorings are mostly renames and type changes.
  Medium-level refactorings shrink classes (median −15 lines), but smell counts barely move
  (Horikawa et al.). **Measured, observational.**
- **Review by a stronger model; architecture rules.** **No measured study found** that tests either
  against degradation over many changes. Only blog posts and opinion.
- **Repository instruction files** are covered in [agent-context-evidence.md](agent-context-evidence.md)
  §6 and [capability-gradient.md](capability-gradient.md). None of them measured structural quality over
  a sequence.

### 2.5 Industry data

- **Cursor adoption, causal mining** ([He, Miller, Agarwal, Kästner, Vasilescu, MSR 2026,
  2511.04427v3](https://arxiv.org/html/2511.04427v3)). 806 adopting repositories against 1,380 matched
  controls, January 2024 to August 2025, staggered difference-in-differences. Lines added rose about
  281% in the first month, and the gain faded within two months. Static-analysis warnings rose 30.3%
  (±6.7) and code complexity 41.6% (±7.6), both persistent. Complexity stays elevated after controlling
  for codebase size (about 9%). Duplicated-line density rose 7.0% (±4.8), **not significant**. The
  authors find the rise in warnings and complexity drives the later slowdown. **Measured,
  peer-reviewed;** this is the strongest field evidence. Limits: adoption is inferred from committed
  `.cursorrules` files, and the model behind Cursor is unknown. The paper's Discussion gives 25% for
  complexity, conflicting with its table.
- **AI-introduced issues that persist** ([Liu et al., "Debt Behind the AI Boom",
  2603.28592v3](https://arxiv.org/abs/2603.28592)). 302.6k AI-authored commits in 6,299 repositories:
  89.3% of introduced issues are code smells, and 22.7% survive to the latest revision. Between 7.5% and
  14.8% of each assistant's commits introduce at least one issue. **Measured mining;** abstract only (the
  PDF body was unreadable), and no human baseline was verified.
- **GitClear 2025** ([report page](https://www.gitclear.com/ai_assistant_code_quality_2025_research)).
  211M changed lines, 2020 to 2024. "Moved" lines (a refactoring proxy) fell from 25% of changes in
  2021 to under 10% in 2024, and copy/pasted lines rose from 8.3% to 12.3%. **Vendor mining:** a time
  trend, not attribution to AI. No method isolates AI, no limitations are stated, and the publisher
  sells code-analysis tools. Widely quoted figures (an "8-fold" rise in duplicated blocks, "50% more
  churn") come from secondary coverage I could not match to the primary page, so they are excluded.
- **DORA 2024** ([Google Cloud announcement, 2024-10-22](https://cloud.google.com/blog/products/devops-sre/announcing-the-2024-dora-report)).
  Higher AI adoption was "accompanied by" an estimated 1.5% drop in delivery throughput and a 7.2% drop
  in delivery stability. The same report associated it with *better* self-rated code quality (+3.4%).
  **Survey, correlational,** before agents. **DORA 2025** reportedly found throughput turning positive
  while instability persisted ([DORA](https://dora.dev/research/ai)); I verified this only through
  summaries.
- **CodeRabbit** ([2025-12](https://coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report)).
  1.7× more issues in 320 AI-co-authored pull requests than in 150 human ones, and 1.64× more
  maintainability issues. **Vendor claim:** small sample, and the publisher sells AI review.

## 3. Counterevidence and limits

- **A preregistered controlled experiment found no maintainability penalty.** Other developers
  extending AI-assisted code showed no systematic difference in completion time or CodeHealth. Code from
  habitual AI users was slightly healthier ([Borg et al., "Echoes of AI", 2507.00788v3; registered
  report](https://arxiv.org/html/2507.00788v3)). The limits are real: it was underpowered (75 of 128
  planned evolvers), the code was human plus autocomplete-era assistant (data collected October 2024 to
  January 2025), and there was one feature, not many. It does not test agents writing whole features.
  It is still the cleanest null result.
- **Small models are not uniquely fragile.** In ChainSWE, GPT-5.4-nano held up as well as GPT-5.5 and
  better than Opus 4.7 under carried-forward state. In SlopCodeBench, Opus 4.7 produced some of the
  most eroded code. If the user's tangled codebases came from Haiku, the evidence suggests an Opus
  session would also have tangled them, measurably, though possibly more slowly. The slope is unmeasured.
- **Patel et al. found agent-built bases sometimes better** (4 cells). The duplication rise in the
  Cursor study was not significant.
- **Erosion happens even with full knowledge of the code.** In SlopCodeBench, the agent extends code it
  wrote itself, with full access to the code. It still patches instead of restructuring. This suggests
  much of the mess comes from an *editing policy* (minimal local change) rather than missing knowledge.
  This is my inference, not a tested result. It matters because comments supply knowledge, not a
  refactoring policy.
- **Metric validity.** Erosion and verbosity are author-defined: verbosity rules came partly from
  observed and social-media anti-patterns, and the complexity cutoff is fixed. SWE-CI's maintainability
  index and SlopCodeBench's metrics are proxies. Patel et al. found static complexity did not predict
  downstream failure. "Tangled" as a user perceives it is not directly measured anywhere.
- **Python dominates, and horizons are short.** ChainSWE averages three steps, Patel et al. two, and
  SlopCodeBench at most about eight. Model versions turn over within months. The Cursor and GitClear
  data predate today's agents or do not record the model.

## 4. Implications

**For #19 (inline skill vs AI-maintained docs folder vs code only, weaker and frontier readers):**

1. **Two-step sequences cannot detect the effect the user describes.** The
   [stage-1 smoke](../evaluation/report-2026-11-07-seq-smoke.md) uses two-step sequences. Degradation in
   SlopCodeBench is a *slope* over about 4 to 8 checkpoints. Patel et al. explicitly could not test
   compounding with two steps. If the claim is "comments prevent the tangle", at least one stage needs
   sequences of five or more changes, with every arm continuing from its own code.
2. **Add structural outcomes beside correctness.** Report SlopCodeBench-style erosion and verbosity (or
   complexity mass and clone lines) per step for each arm, and compare slopes, not only final levels.
   Interpret them cautiously, because Patel et al. found such metrics did not predict the next failure.
3. **Separate knowledge from instruction.** Add a control that gives the *instruction* to keep code
   clean and reuse helpers, with no comments or docs. SlopCodeBench shows that instruction alone
   lowers the starting level of mess. Any inline-arm win must beat that control to count as an effect
   of the comments' *content*.
4. **Test the tier claim symmetrically.** Run a frontier *writer* through the same long sequence, not
   just weaker readers. The evidence predicts both tiers will degrade. The live question is whether
   comments change either slope. Expect wide uncertainty: per-model differences in ChainSWE are a few
   points on about 300 bugs.
5. **Target the mechanisms comments could plausibly affect:** contract drift (Patel et al.'s
   input/error contracts), reuse of existing helpers (detectable with grep), and edits in the wrong
   place (ChainSWE overshoot and undershoot). Erosion from patch-don't-refactor may need a different
   intervention, such as refactoring passes or linter gates. Score those failure classes separately.

**For the corpus (#8):** prefer sources with a human comparison and many steps. SlopCodeBench problems
have both (a human panel, and up to about 8 checkpoints) and its metrics code is reusable. ChainSWE
chains are too short for slope estimates but good for carry-forward errors. Include at least one
sequence where the right move is to *reuse or refactor* an existing helper, so that duplication is
observable.

## 5. Search log

Queries (web, 2026-11-07): `long-horizon coding agent code quality degradation successive edits
maintainability benchmark 2026`; `GitClear 2025 AI code quality research duplicated code moved code churn
report`; `Cursor adoption difference-in-differences static analysis warnings code complexity`; `"Echoes of
AI" downstream effects AI assistants software maintainability`; `DORA 2024 report AI adoption delivery
stability throughput`; `DORA 2025 State of AI-assisted Software Development`; `agentic pull requests
refactoring code duplication AIDev`; `SWE-Chain chained release-level package upgrades`;
`test-driven development coding agents regressions`; `Sonar coding personalities leading LLMs`;
`LLM agent linter feedback code quality static analysis feedback loop`; `CodeRabbit AI-generated pull
requests 1.7x`; `smaller vs larger LLM code quality maintainability code smells`; `reviewer agent
stronger model reviews weaker model code quality`; `AI-generated code technical debt in the wild`;
`EvoCodeBench evolving code generation benchmark`.

Primary pages fetched: SlopCodeBench v2 (full), Patel et al. v1, ChainSWE v2 (first 100k characters),
SWE-CI v4, the Cursor study v3, Echoes of AI v3, Zhu et al. v1, Horikawa et al. v1, TDAD v1, Blyth et
al. (abstract), Liu et al. (abstract), the GitClear page, and the DORA 2024 announcement. The SWE-CI
per-model values exist only as figure images and were not extracted.

Excluded or downgraded:

- **EvoCodeBench** ([Li et al., 2404.00599](https://arxiv.org/abs/2404.00599)). Despite the name, it
  "evolves" by refreshing tasks against contamination; it is not a successive-edit benchmark. A separate
  2026 paper of the same name ([2602.10171](https://arxiv.org/html/2602.10171v1)) evaluates
  self-evolving agents. Neither measures degradation.
- **GitClear secondary figures** ("8× duplicated blocks", "+50% churn", Larridin's 3.3% to 7.1% churn).
  These could not be matched to the primary page.
- **DORA 2025 instability numbers.** These were found only in secondary summaries.
- **"MSR 2026 debt studies" and cross-model review claims** (Codex-CLI blog, SWE-Review blog,
  opinion posts). These are practitioner reports with no inspectable method.
- **Liu et al. body text.** The PDF was unreadable, so only abstract-level figures are used.
- **Quantization and refactoring-capability studies** of model size. These are single-shot and off the
  long-horizon question; they were noted in search only.
