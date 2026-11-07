# Does added context help weaker models more? The capability gradient

Research date: **2026-11-07**, for issue #31 (R2). This is a targeted primary-source review, not a
systematic review. No experiments were rerun. It extends the [coding-agent evidence map](agent-context-evidence.md),
the [expanded comment review](comment-context-deep-dive.md) and the
[LLM evidence distillation](../skill/distillation/llm-evidence.md) (LLM-15, LLM-16, "Which models benefit?").
Studies covered there are cited, not re-summarized. "pp" means percentage points. Relative changes are
labelled as relative. Where I computed a contrast from a published table, it says "my arithmetic".

## 1. Question and bottom line

Does explanatory context help weaker models more than frontier models, and does the benefit shrink as
capability grows?

**The evidence does not support a simple shrinking gradient.** In every study that varies both factors,
the benefit depends on **headroom**: whether the reader lacks the fact *and* can use it. Context helps
least at the floor, where the model cannot exploit it, and at the ceiling, where the fact can be
recovered from code. Context that carries knowledge absent from the code still gave **frontier**
configurations gains of +8 to +25 pp (SkillsBench; most +16 to +20) and roughly tripled their success on
SWE-Bench Pro, although that added context derives from the gold patch and tests. *(Corrected after the [2026-11-07 citation audit](audits/2026-11-07-r1-r4-citation-audit.md).)*
Context that restates what the code shows helps strong models little or not at all, and costs them about
20% more inference. The user's intuition holds best in one form: **weaker models are misled more by wrong
context**, and some within-study contrasts favour weaker readers, though none of those is statistically
significant. No study crosses model tier with maintained context over successive edits. The direct
evidence for #19's question is therefore **weak and indirect**.

## 2. Findings

### 2.1 Effect sizes by tier and setting

| Study (version) | Setting and context | Weaker readers | Stronger readers | Evidence type |
|---|---|---|---|---|
| Pan et al. ([2609.09242v1](https://arxiv.org/html/2609.09242v1), Findings EMNLP 2026), Table 1 | Single-shot LiveCodeBench; correct comment block from a stronger model | Mean gain by recipient (my arithmetic over 3 sources): CodeGeeX4-9B, baseline 19.4%: **+22.8**; Qwen3-8B, 39.2%: +18.1; Seed-Coder-8B, 32.3%: +15.1; Gemma-4-E4B, 54.2%: **+12.6** | No frontier recipient was tested | Measured |
| Gloaguen et al. ([2602.11988v3](https://arxiv.org/html/2602.11988v3), checked 2026-09-29), Table 5 | CTXbench issue resolution; developer-written context file vs none | Qwen3-30B-coder **+7.9**; GPT-5.1 mini +1.5 | GPT-5.2 +2.9; Claude Code with Sonnet 4.5 **−2.9** | Measured; per-cell SE ≈ ±4 pp; the paper's pooled +2.4 pp has p=.21 |
| Same, LLM-generated file vs none | CTXbench / SWE-bench Lite | Qwen3-30B +1.4 / +1.3; GPT-5.1 mini −3.6 / −0.1 | GPT-5.2 +2.9 / −2.2; Sonnet 4.5 **−8.0** / −1.2 | Measured; not significant |
| SkillsBench ([2602.12670v4](https://arxiv.org/html/2602.12670v4), 2026-06-14), Table 2 | 87 agent tasks, 8 domains; curated procedural Skills vs none | Gemini 3.1 Flash Lite 16.0→20.1 (**+4.1**); MiniMax M2.7 18.1→34.9 (+16.8); GPT-5.4 Mini +11.5 | Codex + GPT-5.5 46.8→66.5 (**+19.7**); Claude Code + Opus 4.7 43.0→61.2 (+18.2); OpenHands + Opus 4.8 +8.4 | Measured; across 18 configurations, Spearman ρ between baseline and gain ≈ **−0.09** (my arithmetic) |
| CodeRAG-Bench ([2406.14497v2](https://arxiv.org/html/2406.14497), Findings NAACL 2025), Table 5 | Gold library documentation (DS-1000 / ODEX) | CodeLlama-7B +4.3 / +5.2; StarCoder2-7B +0.8 / +2.9 | GPT-4o −1.5 / −0.4; GPT-3.5 −0.8 / −1.4 | Measured |
| Same | Gold *edited files* on SWE-bench Lite | 7–34B open models 0.0→≤0.7 | GPT-3.5 0.7→6.3; GPT-4o 2.3→30.7 (**+28.4**) | Measured |
| Same | Gold *canonical solution* on HumanEval (answer leak) | StarCoder2-7B **+62.8** | GPT-4o +17.0 | Measured; upper bound only |
| SWE-Bench Pro ([2509.16941v2](https://arxiv.org/html/2509.16941v2), 2025-11-14), Table 3 | Requirements and interface added to the issue, vs issue only | Not tested | GPT-5 (high) 8.4→25.9; Opus 4.1 8.2→22.7 | Measured; no variance reported |

Three patterns emerge.

- **Within a weak tier, lower baselines gained more** (Pan). The four recipients are all 4–9B models, so this
  is a gradient inside the weak tier, not weak versus frontier. Pan's repository replication shows
  gains compressing toward zero when baselines are below 12% or near 67% ([LLM-16](../skill/distillation/llm-evidence.md)).
- **Below a capability floor, context does nothing.** Open 7–34B models could not use oracle files on
  SWE-bench, while GPT-4o gained 28 pp. The weakest SkillsBench configuration gained least. In
  CodeRAG-Bench's words, retrieval helps there only "when paired with strong core generation
  capabilities".
- **When context carries knowledge the code lacks, frontier models gain a lot.** On SkillsBench, gain is
  uncorrelated with baseline, and the authors note that the strongest systems "are not always the
  largest beneficiaries". On SWE-Bench Pro, requirements roughly tripled frontier success. That ablation
  is partly test-shaped, though: the interface names "the class and function names expected by the
  tests", and the requirements are "grounded in the gold patch and test expectations".

Earlier small-model evidence also points both ways. Vitale et al.'s *larger* model gained more from
comments supplied only at inference (+2.33 vs +0.47 pp exact match). RepoQA's weaker DeepSeek-Coder-33B
gained 27 pp when comments were *removed*, against 2.6 pp for GPT-4o. Both are covered in
[agent-context-evidence.md](agent-context-evidence.md).

### 2.2 Scaffolding sensitivity does shrink with capability

Mehtiyev and Assunção analyse 9,374 SWE-bench Verified trajectories from 19 agents
([2604.02547v1](https://arxiv.org/html/2604.02547v1), April 2026). Changing the framework moved Claude 3.5
Sonnet by about **20 pp** but Claude 4 Sonnet by about **4 pp**. Per-task agreement was 85–93% for the
same model across frameworks (Claude 4 Sonnet and Opus 4.5; Claude 3.5 Sonnet 71%), against 47–88% for the same framework across models. This is measured,
observational evidence for the user's intuition, but it concerns the agent scaffold, not explanatory
context. SkillsBench offers an analogue by domain: software engineering had among the smallest gains
(+11.6 pp, 37.6→49.2). The authors attribute small gains to domains with strong pretraining and tooling
coverage.

### 2.3 Where frontier agents still fail without added context

- **Multi-file changes.** With Claude 3.5 Sonnet, three tools solved about 55–58% of single-file
  SWE-bench Verified issues but only **11–25%** of multi-file ones. Agentless solved 12 of 13 multi-file
  issues it passed with single-file edits. "Ignoring semantic dependencies" is a named failure
  subcategory, and knowledge deficiency causes about 25% of failures ([Liu et al., 2509.13941v1](https://arxiv.org/html/2509.13941v1), September 2025; measured, manual taxonomy of 150 failures).
- **Architectural layer.** On the 12 simple-patch tasks (a subset of 55 that no agent solved), including Opus 4.5 agents at about 79%
  overall, the best agent found the right file in all 12 but fixed the symptom rather than the root cause ("wrong layer" is this report's paraphrase) in **10 of 12**
  tasks ([Mehtiyev and Assunção](https://arxiv.org/html/2604.02547v1); measured, small sample).
- **Large edits.** On SWE-Bench Pro (reference patches average 4.1 files and 107 lines), the authors
  report that top models "struggle to produce solutions on high-complexity tasks", failing mainly on
  semantic correctness. Weaker models fail more on "syntax, formatting, and tool-use". Frontier models
  stay above 10% on tasks touching 10 or more files, while open models approach zero
  ([2509.16941v2](https://arxiv.org/html/2509.16941v2); measured with an LLM judge; models as of September 2025).
- **Successive edits.** ChainSWE and SWE-CI show frontier regressions over dependent changes
  ([agent-context-evidence.md §7–8](agent-context-evidence.md)).

These are the non-local cases the user names. None of these studies tested whether a comment or document
would have prevented the failure.

### 2.4 Harm: cost and distraction for strong models, being misled for weak ones

**Strong models.**
- Generated context files raised cost 20–23% with no accuracy gain. Sonnet 4.5's −8.0 pp on CTXbench is
  the largest single drop, though not significant ([Gloaguen](https://arxiv.org/html/2602.11988v3)).
- **Self-generated** Skills cut frontier configurations by −8.1 (Opus 4.7), −11.3 (GPT-5.5) and −11.5 pp
  (Gemini 3.1 Pro). Comprehensive documentation gained only +0.7 pp, against +19 to +21.5 pp for focused
  Skills. 13 of 87 tasks got worse with Skills, when a Skill displaced "a stronger default strategy"
  ([SkillsBench v4](https://arxiv.org/html/2602.12670v4)).
- Misleading hint comments cut Claude 3.5 Sonnet by 43.4% (relative) on LiveCodeBench output prediction.
  In reasoning models (o3-mini-high, DeepSeek-R1, QwQ) they also inflated reasoning tokens 2–3× ([CodeCrash v3](https://arxiv.org/html/2504.14119v3), NeurIPS 2025, Table 1).
- Efficiency can improve as well. AGENTS.md was associated with a 28.6% lower median runtime and 16.6%
  fewer output tokens on 124 PRs with Codex, with no tier comparison ([Lulla et al., 2601.20404](https://arxiv.org/html/2601.20404); measured, paired, small).

**Weak models are misled more.** In CodeCrash, misleading code comments cut GPT-4o by 14.0% and 29.1%
(relative, CRUXEval and LiveCodeBench) but GPT-4o-mini by 32.6% and 40.4%. Misleading hint comments cut
Claude 3.5 Sonnet by 14.4% and 43.4% but Claude 3.5 Haiku by 27.5% and 53.3%. Reasoning models were
mostly robust (DeepSeek-R1 ≤3.5%), though o3-mini-high lost 28.4% under hint comments. Macke and Doyle
find wrong documentation cost GPT-3.5 about 22.6 pp against about 10.4 pp for GPT-4
([LLM-15](../skill/distillation/llm-evidence.md)). Pan's wrong-topic comments cut weak recipients by
15–34 pp. Of all the user's claims, this one has the most consistent direction across studies.

### 2.5 Practice closest to the user's docs folder

*Codified Context* ([2602.20478](https://arxiv.org/html/2602.20478), February 2026) is a **practitioner
report**: one developer, one C# game, Claude Code, about 26,000 lines of agent-facing specifications. It
reports no save-system bugs across 74 sessions that consulted a 283-line spec. It names **specification
staleness** as "the primary failure mode": outdated specs twice led agents to write code that conflicted
with recent refactors. Maintenance cost about 1–2 hours a week. There is no control condition and no
model-tier comparison. The report supports the user's experience and the two-sources-of-truth concern
together.

## 3. Counterevidence and limits

- **The tiers are not today's tiers.** Pan's "weak" models are 4–9B. Gloaguen's weakest is
  Qwen3-30B. CodeCrash compares 2024 models. Haiku 4.5 scored 39.5% on SWE-Bench Pro's public set
  against 43.6% for Sonnet 4.5 (different caps than the ablation). If that ~4 pp gap carries over to
  the Haiku 5.5 and Sonnet 5.5 generation, it is far smaller than any contrast above.
- **Per-tier contrasts are underpowered.** Gloaguen's tier differences sit within about two standard
  errors. Khatri's two-agent ablation ([2607.27250v1](https://arxiv.org/html/2607.27250v1)) found no
  effect (Sonnet 4.6: 53.3% none, 55.6% always-on, 55.6% selective), with a minimum detectable effect
  above 30 pp.
- **Context type differs across studies.** Skills are procedural knowledge. Pan's comments describe
  solutions. SWE-Bench Pro supplies requirements. Gloaguen's files are repository guidance. None is a
  maintained description of "what the code does", the layer the skill targets.
- **Oracle and answer-derived context inflates the numbers.** HumanEval gold documents are the
  solutions. Pan's source comments are filtered on passing tests. SWE-Bench Pro requirements derive
  from the gold patch.
- **SkillsBench is not code maintenance.** It spans eight domains, and its software-engineering slice
  is small.
- **Counterevidence searched for and not found:** a study showing frontier coding agents are *harmed*
  by accurate, non-redundant, task-relevant context on average; and any tier comparison under naturally
  stale comments (*When Comments Mislead* is still abstract-only).

## 4. Implications

**For the skill's content.** The "what the code does" layer is the information a frontier reader can
most easily recover from code. Context of that kind did not help or hurt strong agents measurably, and it
added cost (Gloaguen's documentation-removal ablation; SkillsBench's flat result for comprehensive docs).
The evidence points the skill at facts the code does not show: cross-module effects, the correct layer,
rejected alternatives and external constraints. That is where frontier agents still fail (§2.3). The
skill also has to treat accuracy as more important the weaker the reader, because weaker readers are
misled more (§2.4). Self-generated Skills underperformed in SkillsBench, so #19 must test context that
the skill *writes*. Curated context is only an upper bound.

**For #19's reader tiers.**
1. **Select tiers by measured headroom, not by name.** Run the code-only arm first and choose readers
   whose strict reader-step success falls between about 25% and 75%. Floors and ceilings hide effects
   (Pan, CodeRAG-Bench, SkillsBench).
2. **Use three tiers if the harness allows it with equal tools.** Haiku 5.5 versus Sonnet 5.5 tests only
   a narrow gradient. Add a frontier ceiling (Opus 5.5). If possible, add a genuinely weaker reader in
   the same harness. Otherwise state that the gradient tested was Haiku to Sonnet only. Two points cannot
   reveal the inverted-U pattern that §2.1 suggests.
3. **Cross tier with fact type.** Include reader steps whose needed fact is visible locally in code
   (prediction: no frontier benefit) and steps whose fact is non-local or absent from the code
   (prediction: benefit at every tier with headroom). This tests the mechanism the user proposes,
   "frontier models read the code", directly.
4. **Score harm per tier.** Record tokens and cost per reader step, as the strong-model harm, and errors
   under the drift condition, as the weak-model harm.

**Minimum effect worth detecting.**
- **Per-tier main effect** (context arm minus code-only, and inline minus docs): plan for **10 pp**
  strict reader-step success. The reasons:
  - Effects of 2–8 pp went undetected in Gloaguen, with 138–300 tasks.
  - Run-to-run noise alone is 2–6 pp ([evaluation protocol](evaluation-protocol.md)).
  - When context carries missing knowledge, published effects reach 10–25 pp.
  - Practitioner maintenance costs about 1–2 hours a week, so an effect much below 10 pp is unlikely to
    repay it. That last point is a judgment, not a measurement.
- **Rough sizing** (paired normal approximation, α=.05, 80% power, *independent* pairs before clustering):
  if 20–30% of pairs are discordant, a 10 pp effect needs about **160–240** reader steps per tier, and a
  20 pp effect about 40–60. The 5 pp floor in the protocol's example needs about 630–940.
- **Tier interaction** (difference in differences, the user's actual claim): a 10 pp interaction needs
  about **310–470** steps per tier, and 15 pp about 140–210. #19's 10-sequence pilot cannot test the
  interaction. Report it descriptively with intervals, and fund a confirmatory test only if the pilot
  estimate is at least about 15 pp. Repository clustering will raise all of these numbers.

**For the corpus (#8).** Over-sample tasks with cross-file or cross-layer dependencies (three or more
files, contracts that span modules) and tasks in each reader's headroom band. Also include matched
local-fact control tasks. Single-file tasks near either reader's floor or ceiling will dilute the effect
toward zero.

## 5. Search log

Queries run on 2026-11-07, with web search and direct fetches:
- `SkillsBench agent skills benchmark curated skills pass rate improvement by model smaller models`
- `CrossCodeEval cross-file context retrieval improvement by model size results`
- `CodeCrash misleading comments perturbation LLM code reasoning frontier models`
- `AGENTS.md context files coding agents effect per model 2026 arxiv efficiency study`
- `CodeRAG-Bench documentation retrieval helps weaker models more than GPT-4o results`
- `empirical study failures coding agents SWE-bench cross-file dependencies non-local constraints failure taxonomy`
- `Lulla AGENTS.md efficiency …`
- `"When Comments Mislead" outdated comments …`
- `SWE-bench hints ablation …`
- `repository documentation generated wiki improves small open models …`
- `SWE-Bench Pro frontier failure analysis multi-file …`
- `CodeUpdateArena … GitChameleon …`
- `Chroma "context rot" …`
- `aider architect mode …`
- `LLM codebase question answering with documentation vs code only …`
- `"Codified Context" …`
- `small language model … knowledge graph or documentation …`
- `effect of code comments on LLM program comprehension across model sizes …`

Fetched and used: the arXiv HTML of SkillsBench v4, Gloaguen v3 (Table 5), CodeRAG-Bench v2 (Table 5
and gold-document definitions), CodeCrash v3, SWE-Bench Pro v2, Liu et al. v1, Mehtiyev and Assunção
v1, Khatri v1 (alphaXiv abstract page), Codified Context and SWD-Bench. Table values reached me through a
fetch tool's extraction. I cross-checked the SkillsBench and Gloaguen rows against each paper's
published means and they matched. All other values are unverified beyond that extraction.

Excluded:
- **CrossCodeEval (2023)**: no per-size table retrieved, and it predates current models.
- **CodeUpdateArena, GitChameleon**: only secondary summaries reached.
- **Chroma *Context Rot***: a vendor report on non-code retrieval, read only through search summaries.
- **Aider architect mode**: a practitioner benchmark of an edit-format split, not explanatory context; not fetched.
- **SWD-Bench ([2604.06793](https://arxiv.org/html/2604.06793))**: two 2025 frontier answerers and no
  code-only arm. It does show documentation and code as complementary.
- **benchmarklist.com, Medium, dev.to, liner, themoonlight, emergentmind**: secondary or self-reported
  summaries, used for discovery only.
- **Sabetto et al. ([2506.11007](https://arxiv.org/html/2506.11007v1))**: on inaccurate comments in legacy
  code; not checked for model-size results. This is a follow-up.
- ***When Comments Mislead***: still no full text found.
