# Can a cheap model implement what a strong model planned?

Research date: **2026-11-07**, for issue #36 (R6). This is a targeted primary-source review, not a
systematic review. No experiment was run. It extends [capability-gradient.md](capability-gradient.md)
(R2), which covers SWE-Bench Pro's requirements ablation, SkillsBench, CTXbench and the wrong-layer
failures; those are cited here, not re-summarized. "pp" means percentage points. Where I computed a
number from a published table it says "my arithmetic". Cost per success is total spend divided by tasks
solved.

Evidence types: **measured** (an experiment with a stated method), **survey**, **practitioner report**,
**vendor claim** (including product documentation and vendor-run benchmarks).

This report is written to support a decision. Where the evidence is thin, it says so.

## 1. Question and bottom line

If a strong model or a human decides what a feature is and must do, can a cheap model such as Haiku
write the code? Does richer context close the gap, and what does that imply for comments?

**A plan written upfront helps a cheap executor a lot, but it does not make it the planner's equal.**
The cleanest experiment (DCAS, ASE '26) gave a 30B open model plans from Claude Sonnet 4.5. That lifted it
from 42.8% to 57.8% on SWE-bench Verified. Its own self-made plan scored 48.2%. Sonnet 4.5's vendor-reported
solo score is 77.2% ([Anthropic, 2025-09-29](https://www.anthropic.com/news/claude-sonnet-4-5), different
scaffold), so the plan recovered roughly 40% of the gap (my arithmetic). In the only study that
reports cost (Gandhi et al., 2025), "strong plans, weak executes" was the **most expensive option per solved
issue**. The planning call cost almost as much as letting the strong model solve the issue. **Implementation
contains real decisions**, such as where code goes, what to reuse and which layer to change. Plans that omit
them do not transfer well, and a poor plan is worse than none. The hybrids that do match strong-model quality
at lower cost keep the strong model **in the loop during execution**: an advisor called before work and before
"done", the strong model drafting while the weak one repairs, or a router that escalates hard steps. One-shot
plans do not. Cheap models are reliably good at narrow, mechanical edits. On hard agentic coding, the current
Haiku trails Sonnet by a wide margin (39.2% vs 70.6% on Anthropic's Terminal-Bench 4.0). **Your distrust is
broadly supported for open-ended implementation, and not supported for well-scoped edits.** No study tests
code comments as the carrier of the plan.

## 2. Findings

### 2.1 Planner/executor and architect/editor splits

| Study (version, date) | Strong role → cheap role | Result | Cost | Evidence |
|---|---|---|---|---|
| **DCAS** ([Thangarajah, Chen, Hassan, ASE '26](https://arxiv.org/abs/2608.06113); DOI 10.1145/3832783.3834485), Table 4 | Planner writes a ≤8-step repair plan after up to 500 exploration turns → Qwen3-Coder-30B-A3B executes in Claude Code | SWE-bench Verified Pass@1: no plan 42.8; self-plan 48.2; Qwen3-480B plan 49.2; Opus 4.5 plan 54.2–56.0; **Sonnet 4.5 plan 57.8** | Not reported | Measured; single run, n=500. The authors say plan quality "scales with planner capability" |
| **Gandhi et al.** ([2505.20182v1](https://arxiv.org/html/2505.20182v1), May 2025, arXiv), Table 3 | o4-mini plans (localization, root cause, approach; no code) → GPT-4o-mini patches. Agentless Lite, SWE-bench Lite | Weak alone 15.3%; **Plan 29.3%**; strong alone 45.3% | Per resolved issue (my arithmetic): weak $0.10, strong $0.25, **Plan $0.34** | Measured; 300 issues, one run |
| Same, other pairs (Table 7) | o3-mini plans → Qwen2.5-Coder-7B / 32B | 7B: **8.3%**, and its valid-patch rate fell to 0.52. 32B: 25.3% vs 20.3% alone and 33.7% strong | Plan cost ≈ 3–4× the weak model alone | Measured |
| **Aider architect mode** ([2024-09-26](https://aider.chat/2024/09/26/architect.html)) | Architect describes the fix in prose → editor writes the edit | Every pair beat the architect alone (o1-preview 79.7 → 85.0; Sonnet 3.5 77.4 → 80.5; GPT-4o 71.4 → 75.2) | Not given | Practitioner benchmark; one run per cell, no variance |
| Aider leaderboard ([updated 2025-11-20](https://aider.chat/docs/leaderboards/)) | o3 (high) → GPT-4.1; R1 → Sonnet 3.5 | o3+4.1: 78.2% vs o3 (high) 81.3% and o3 76.9%. R1+Sonnet: 64.0% vs Sonnet 51.6% and R1 56.9% | Per solved exercise (my arithmetic): o3+4.1 $0.10; o3 (high) $0.12; o3 $0.08 | Practitioner benchmark |
| **Anthropic advisor tool** ([blog, 2026-04-09](https://claude.com/blog/the-advisor-strategy); [docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool)) | Opus advises on demand, seeing the full transcript → Sonnet or Haiku executes | Sonnet 4.6, SWE-bench Multilingual: **+2.7 pp** (5 trials × 300). Haiku 4.5: **no coding result**. BrowseComp 19.7 → 41.2, still "29%" below Sonnet alone | Sonnet: −11.9% per task. Haiku pair: "85% less" than Sonnet | Vendor claim |

What the splits show:

- **The Aider gains are not "cheap model implements".** Aider's editor turns a finished solution into
  correctly formatted edits. The post's stated motive is that o1 models "often fail to output properly
  formatted code editing instructions". Its best editors were themselves frontier-class at the time
  (Sonnet, o1-mini, DeepSeek). The record result put the **cheaper model (R1) as architect and the stronger
  coder (Sonnet) as editor**. Pairing o1 with Sonnet did not beat o1 alone. Aider never tested a
  Haiku-class editor. The o3+GPT-4.1 pair scored below o3 (high) alone.
- **The advisor design keeps the strong model in execution.** Anthropic's coding guidance calls for about
  2–3 advisor calls per task: one after orientation and one **"before declaring done"**. The docs state that
  the benefit shrinks as the executor approaches the advisor's capability. Their best fit for Haiku is
  narrowly scoped work. The only coding number is for a Sonnet executor.
- **Plan quality matters in both directions.** In COPE ([2506.11578v3](https://arxiv.org/html/2506.11578v3),
  January 2026; MATH-500), a GPT-4o-mini plan lifted Llama-3B from 42.8% to 53.0%. A weaker planner pulled
  GPT-4o-mini down, from 73.8% to 69.6–70.6%. On SWE-agent, Liu et al. find that "a subpar plan hurts
  performance even more than no plan at all" ([2604.12147v1](https://arxiv.org/html/2604.12147v1), April
  2026; measured, 16,991 trajectories). They also find that capable models override plans that do not fit
  the task.

### 2.2 Implementation is not separable from thinking

- **Developers make design decisions while coding.** Liang et al. interviewed and surveyed 53
  professionals ([2301.09789v1](https://arxiv.org/abs/2301.09789), January 2023). They found implementation
  decisions about data, structure, reuse, APIs and code constructs. These "require constant monitoring of
  higher level design choices", and requirements changed during implementation. *Survey and interviews;
  qualitative, no frequencies.*
- **Knowing *where* does not finish the job.** Sepidband et al. gave GPT-5-mini the developer patch's exact
  files, functions and lines ([2604.05481v1](https://arxiv.org/html/2604.05481v1), April 2026; measured, one
  attempt). It resolved 59.8% of SWE-bench Verified, against 56.2% with files only. **40% stayed unresolved
  despite perfect localization.** Its 3.6% no-localization baseline gave the model no repository retrieval,
  so do not read the jump as a localization effect.
- **Plans must reach implementation detail.** RealBench ([2604.22659v2](https://arxiv.org/html/2604.22659v2),
  July 2026; measured) removed class diagrams and kept only the package-level architecture. Claude Sonnet 4's
  incremental test pass rate fell from 17.5% to 6.2%, and Qwen3-235B's from 19.5% to 3.3%. The authors
  conclude that high-level design "is insufficient without implementation details". The paper's text and
  tables differ slightly on the averages.
- **Agents duplicate instead of reusing.** Huang et al. used semantic clone detection on 617 crewAI PRs
  ([2601.21276v1](https://arxiv.org/html/2601.21276v1), MSR '26). Agent PRs had about **1.87×** the human
  redundancy, and "LLM Agents frequently disregard code reuse opportunities". LOC and cyclomatic complexity
  barely differed, so tests and simple metrics miss this. *Measured; one repository, no per-model split.*
- R2 §2.3 already covers the "wrong layer" failures: Opus-class agents fixed symptoms in 10 of 12 simple
  tasks. It also covers SWE-Bench Pro's finding that frontier failures are semantic rather than syntactic.

Together these explain why plans transfer only partly. The decisions that separate a good patch from a
passing one are made at the point of edit, and a plan written before reading the code rarely contains them.

### 2.3 Does richer context let weaker models match stronger ones?

Extending R2 (SWE-Bench Pro requirements, SkillsBench, CTXbench):

- **Repository-level context did not help the weak model. Instance-level help did.** In Gandhi et al.,
  repo summaries, repo FAQs, repo structure and few-shot examples left GPT-4o-mini at 13.7–15.7%, against its
  15.3% base. Qwen-32B fell from 20.3% to 17.0–18.3%. The authors write that repo-level context "consistently
  failed to improve weak LM performance". Plans and instance-level Q&A did help, but cost close to
  strong-model prices. *Measured.* **This is the closest published analogue to a generic docs folder, and it
  is negative.**
- **Code quality helps mid-size models, not Claude.** Borg et al. ran refactoring on 5,000 Python files
  ([2601.02200v1](https://arxiv.org/html/2601.02200v1), January 2026, FORGE 2026). On healthy code, five 20–30B
  open models broke tests 15–30% less often (relative risk 0.69–0.85, all significant). Sonnet 4.5 (13.2%
  vs 16.0%) and agentic Claude Code (3.8% vs 5.2%) showed no significant difference. *Measured.* This
  supports the capability claim, but for code structure, not prose context.
- **Detailed design narrows gaps at low absolute levels.** With full UML design, RealBench's
  Qwen2.5-Coder-7B averaged 14.3% against Claude Sonnet 4's 17.4% (my averages of the paper's Table 5).
  There is no no-design baseline per model, so this does not show the gap *closing*.
- **Instruction plans help everyone.** DCAS's self-plan gave +5.4 pp and Liu et al.'s plan reminders improved
  success. Part of any gain from external plans is structure, not the planner's knowledge.

### 2.4 Hybrids with measured cost per success

| Pattern | Source | Quality | Cost | Evidence |
|---|---|---|---|---|
| Strong drafts, weak repairs formatting ("Strong LM First") | Gandhi et al. | 41.7% vs strong 45.3% | **$0.20** per resolved issue vs $0.25 strong (my arithmetic) | Measured; best method in the paper |
| Weak first, strong on failure | Same | 15.3%, no better than weak alone | Cheapest | Measured. Escalation keyed to *invalid* patches, not wrong ones, catches little |
| Step-level router: DeepSeek V3.2 vs Opus 4.6 | [TwinRouterBench 2605.18859](https://arxiv.org/html/2605.18859) (v5, May 2026) | Trained router 75/100 vs Opus alone 74/100 | $25.66 vs $54.73 (−53%) | Measured; 100 non-random Django/Astropy instances, one run |
| Same, Opus as an LLM router | Same | Flagged 7 of 147 hard steps; failed all 40 SWE trajectories | n/a | Measured; one prompt |
| Which steps need a strong tier | Same, static track | Test/verify/debug 72% high or mid-high; code patching 50%; tool calls <1% | n/a | Measured labels; workload-confounded |
| Advisor (Sonnet executor) | Anthropic | +2.7 pp | −11.9% per task | Vendor claim |
| Test-gated cascade, small to large | [Chen et al. 2405.15842v2](https://arxiv.org/abs/2405.15842v2) | Roughly maintained, per the abstract | −26% average, up to −70% | Measured on function-level benchmarks; abstract only |

No study measures **a strong model reviewing a weak model's diff** for repository-level code. The
review-shaped evidence is the routing labels above, where verification steps most need the strong tier.
Another is Aider's editor role in reverse.

### 2.5 Where small models do implement well

- **Mechanical application.** Cursor's fine-tuned Llama-3-70B apply model "almost matches" Claude 3 Opus at
  applying a planned edit across about 450 full-file edits, roughly 13× faster
  ([2024-05-14](https://cursor.com/blog/instant-apply); vendor claim, graded by Opus). This is the industrial
  architect/editor split. The small model's job is deliberately decision-free.
- **Current small Claude models.** Haiku 4.5 reported 73.3% on SWE-bench Verified, "matching Sonnet 4"
  at about a third of the cost ([2025-10-15](https://www.anthropic.com/news/claude-haiku-4-5); vendor claim,
  50 trials). Haiku 5.5 is priced at $0.10/$0.50 per million tokens against Sonnet 5.5's $2/$10, 20×
  cheaper. It scores 46.4% vs 52.1% on FrontierCode 1.1, but 39.2% vs 70.6% on Terminal-Bench 4.0
  ([2026-10-07](https://www.anthropic.com/news/claude-haiku-5-5); vendor claim). Anthropic itself says Sonnet
  and Opus "remain better choices for complex agentic coding". If token use were equal, Haiku's cost per
  Terminal-Bench success would be about a tenth of Sonnet's (my arithmetic). That assumption is unverified,
  and it ignores the cost of wrong changes that pass.
- **A 3B-active model with a frontier plan** reached 57.8% on SWE-bench Verified (DCAS). That is well above
  2024 frontier solo scores.
- **COPE** matched or beat GPT-4o on MBPP at about a quarter of the cost, with 1.5–2.4B models in the loop.
  These are function-level tasks, so the result says little about repositories.

## 3. Counterevidence and limits

- **Against the user's distrust.** Within a frontier generation the gap is sometimes small: 6 pp on
  FrontierCode, and Haiku 4.5's 73.3% Verified score. Routing and advisor setups matched strong-model quality
  at half the cost or less. If tasks are narrow and well verified, a cheap implementer is economically
  rational.
- **Against "plan upstream, then hand off".** Every quality-preserving hybrid kept the strong model active
  during or after execution. The one-shot plan was the costliest per success. The DCAS plan still left a
  roughly 20 pp gap to the planner's (vendor) solo score. DCAS did not run the planners alone, so that
  comparison crosses sources.
- **Executors in the measured studies are not Haiku 5.5.** They are GPT-4o-mini, Qwen 7–32B and a 30B-A3B
  Qwen. The only Haiku executor result is BrowseComp, a browsing benchmark. **No published measurement covers
  Haiku 4.5 or 5.5 executing a stronger model's coding plan.**
- **Single runs everywhere.** DCAS, Gandhi, Aider and TwinRouterBench report one run, and SWE-bench run-to-run
  noise is 2–6 pp ([evaluation protocol](evaluation-protocol.md)). Aider and Anthropic numbers are vendor- or
  practitioner-run.
- **Tests understate the weak executor's real cost.** Redundancy (Huang et al.) and symptom-level fixes (R2)
  pass tests. Cost per success excludes review time and later rework. Those are exactly the costs the user's
  distrust is about.
- **Counterevidence searched for and not found:** a study in which a cheap executor with a frontier plan
  *matched* frontier solo performance on repository-level tasks, and any study of comments or inline notes
  as the plan carrier.

## 4. Implications

**For the Code Comments thesis.** The evidence suggests an answer to "could comments carry the plan to the
point of edit?", though it is untested.

- *What a task plan cannot carry and a comment might.* A plan is task-specific and written before the code
  is read. The failures that survive plans are standing, location-bound decisions: reuse this helper, this
  layer owns the rule, this invariant spans these modules. A comment at the point of edit can state those
  durably, and it is read exactly when the executor makes the decision (§2.2). That is the strongest argument
  for the thesis in this report.
- *What argues against.* Generic repository context did not help a weak executor (Gandhi et al.). Comments
  that describe what code does are closer to that than to an instance-level plan. Only the non-derivable,
  location-specific content has support, which is R2's conclusion again. Weak readers are also the most
  misled by wrong context (R2 §2.4), so a stale comment acts like a "subpar plan", which was worse than none.
- *What it would not replace.* Comments cannot replace the task-level decision about what the feature must
  do. Nor do they remove the need for verification by a strong model or tests. Every hybrid that preserved
  quality had one or the other.

**For #19.** #19's stage-1 already has a Sonnet 5.5 writer and a Haiku 5.5 reader, so it is structurally a
planner/executor split. Add two cheap arms so the result answers the user's question directly:
1. **Plan-only.** Sonnet writes a task plan for the reader step, with no comments or docs. This separates
   "strong upstream thinking" from "persistent context at the point of edit". If inline comments do not beat
   plan-only, the thesis's mechanism is not supported.
2. **Ceiling.** Sonnet performs the reader step itself, so retention can be stated as a share of the gap
   closed, as in §1.

Report **cost per successful step** for every arm, including writer tokens. Score **reuse and duplication**
and **wrong-layer** edits as well as tests, because weak executors' failures pass tests.

**For #8 (corpus).** Tag tasks where the correct change requires reusing an existing helper, editing a
specific layer, or keeping a cross-module invariant. These are the decisions plans miss and comments could
carry. Include matched tasks with no such decision, as a control on which a plan alone should suffice.

## 5. Search log

Queries (2026-11-07):
- `Anthropic advisor tool Claude Opus advisor Haiku executor benchmark`
- `aider leaderboard architect editor 2025 polyglot …`
- `arxiv strong planner weak executor code generation small model implements plan … SWE-bench`
- `arxiv 2025 "plan" guidance large model small model code generation transfer …`
- `Claude Haiku 5.5 SWE-bench Verified score Sonnet 5.5 comparison`
- `LLM generated code duplication reuse existing functions repository empirical study …`
- `empirical study coding agents follow plan deviate … 2026`
- `empirical study design decisions made during implementation …`
- `SWE-bench oracle localization ablation …`
- `strong model reviews weak model code patches … verifier critic`
- `LLM cascade code generation cheap model first escalate …`
- `model routing coding agent SWE-bench cost per resolved issue …`
- `Borg 2026 code health LLM refactoring …`
- `detailed specification improves smaller LLM code generation … 2026`

Fetched and used: the Aider architect post, R1+Sonnet post and leaderboard; the Anthropic advisor blog and
docs; the Haiku 4.5 and 5.5 announcements; Claude Code model-config docs (`opusplan`: Opus plans, Sonnet
executes, a vendor default that pairs with Sonnet, not Haiku); and the arXiv HTML of Gandhi et al., COPE,
Liu et al., Sepidband et al., RealBench v2, Huang et al., Borg et al., TwinRouterBench, Triage and Liang et
al. For DCAS I extracted the PDF text locally and read Tables 3–4. Table values for the other sources came
through a fetch tool's extraction and were not independently re-checked.

Excluded:
- **SHERLOC (2606.24820)**: the oracle condition could not be confirmed from the abstract.
- **SWE-RPG (2608.09072)**: gold plans are used only to validate the benchmark and are never given to agents.
- **Triage (2604.07494)**: it proposes an evaluation but reports no results.
- **Self-planning (2303.06689) and CodePLAN (2403.13271)**: 2023–24 models, function-level tasks, read
  only through search snippets.
- **Haiku 5.5 SWE-Bench Pro figures (64.8 vs 81.3)**: they appear only on a third-party blog, not on
  Anthropic's page.
- **Real-SWE cost figures, apidog, dev.to, mindstudio, builder.io and other secondary advisor posts**:
  secondary sources, used for discovery only.
- **The 2024 Aider claim that DeepSeek helps "all the Architect models except for Sonnet"** contradicts
  the post's own table (78.9 vs 77.4), so the table was used.
