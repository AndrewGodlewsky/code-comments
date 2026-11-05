# Benchmarks for testing comments through successive edits

Status: primary-source research and proposed reuse, accessed 2026-11-05. No
benchmark was installed or executed, and no model experiment was run locally.

**Start with SlopCodeBench for controlled evolving specifications, ChainSWE for
maintenance of real repositories, and ContextBench-style retrieval measurement.**
SWE-CI and SWE-Milestone offer valuable later stress tests, but require more work
to separate comment placement from changing requirements or conversational memory.
This is a corpus recommendation, not an accepted implementation decision.

None of these benchmarks independently establishes that comments can replace
documents. They supply tasks, environments, tests, and measurement patterns. The
matched factual content, placement intervention, explanation-maintenance checks,
and complete cost accounting still have to be added. The
[evaluation protocol](evaluation-protocol.md) owns those experimental decisions.

## What the benchmarks actually measure

Counts below describe the named paper or release, not an interchangeable current
leaderboard. F2P means tests failing before a reference change and passing after;
P2P means previously passing tests that should remain passing. Passing those tests
establishes correctness against that evaluator, not all possible requirements.

| Benchmark and primary source | Task/sample and sequence handling | Execution and regression checks | Reusable component; required adaptation |
| --- | --- | --- | --- |
| [SlopCodeBench, Orlanski et al., v2](https://arxiv.org/html/2603.24755v2), §§2–3 | 36 problems, 196 checkpoints; agent extends its own code under successive specifications | Strict checkpoint success requires current and earlier tests; separate isolated/current-core scores | Sequence runner and black-box tests; add matched fact inventories and explanation scoring |
| [ChainSWE, Jin et al., v2](https://arxiv.org/html/2607.02606v2), §§3–4 | 100 chains, 304 bugs, 54 Python repositories; oracle, fresh-chat cumulative-code, and cumulative-chat modes | Per-bug and whole-chain outcomes using inherited test assets | Most direct persistent-repository comparison; validate cumulative test coverage and matched task visibility |
| [SWE-CI, Chen et al., v4](https://arxiv.org/html/2603.03823v4), §§2–3 | 100 base/target pairs across 68 repositories; adaptive architect/programmer iterations toward target tests | Normalized test improvement/regression, aggregated as EvoScore | CI-loop infrastructure; freeze requirements for placement study or explicitly study adaptive policy |
| [SWE-Milestone, Deng et al., v4](https://arxiv.org/html/2603.13428v4), §§3–5 | Seven real repository release histories reconstructed into milestone DAGs; continuous agent session | Milestone F2P/P2P outcomes, partial progress and full resolution | Dependency-aware history and checks; add session boundaries and audit underspecified assertions |
| [SWE-EVO, Thai et al., v1](https://arxiv.org/html/2512.18470v1), §3 | 48 release-evolution tasks from seven Python projects | Resolved Rate and Fix Rate; F2P plus P2P | Substantial multi-file changes; needs explicit successive-session decomposition |
| [SWE-bench Verified](https://github.com/SWE-bench/SWE-bench), README | 500 human-filtered issue tasks; independent repository snapshots | Issue-resolution harness with regression tests | Familiar harness sanity checks; inherited defects/contamination make it a weak primary corpus |
| [SWE-bench Pro V2, Scale AI](https://github.com/scaleapi/SWE-bench_Pro-os/blob/main/v2/README.md), layout/protocol | 642 public tasks; HARD-51 subset; independent tasks, not repeated maintenance | Fresh-sandbox patch replay; oracle/empty-patch release checks | Strong isolation practices; requires new sequences and factual annotations |
| [SWE-ContextBench, Zhu, Hu, Wu](https://github.com/jiayuanz3/SWEContextBench), README | Current repository: 1,007 base and 362 related tasks, 53 repositories, nine languages | SWE-bench-style patch evaluation and related-task images | Experience-reuse pairs; must distinguish retrieved prior solutions from persistent project knowledge |
| [CTXbench, Gloaguen et al., v3](https://arxiv.org/html/2602.11988v3), §3 | 138 tasks in 12 repositories with developer context files; independent tasks | Generated/reviewed task tests plus repository tests | Existing context-file comparisons; replace unequal content with matched inline/external facts |
| [VibeMemBench, Fan et al., v1](https://arxiv.org/html/2609.23570v1), §§3–4 | 111 target tasks, 90 repositories, 3,634 prior trajectories; outcome-selected memory-sensitive tasks | Executable target resolution, memory-on/off comparison | Prior-experience construction and retrieval controls; account for selection and full memory costs |
| [DreamBench-SWE, Singh, v1](https://arxiv.org/html/2608.20664v1), §§5–6 | 60 curated three-session traps, three seeds; prior knowledge absent from final request | Hidden behavioral oracles and memory/no-memory contrasts | Cross-session diagnostic patterns; curated recall and incomplete public evaluator limit generalization |
| [ContextBench, Li et al.](https://github.com/EuniAI/ContextBench), overview | Current README: 1,136 issues, 66 repositories, eight languages; gold retrieval context | Trace coverage/precision at multiple granularities; supplements task success | Retrieval instrumentation; add comment/document fact IDs and actual use checks |
| [RepoQA, EvalPlus team](https://github.com/evalplus/repoqa), SNF | 500 function-retrieval cases in five languages; no evolution | Parsed function similarity, not execution | Cheap retrieval diagnostic; cannot establish editing correctness |
| [CrossCodeEval, Ding et al.](https://github.com/amazon-science/cceval) / [RepoBench, Liu, Xu, McAuley](https://arxiv.org/abs/2306.03091) | Cross-file completion/retrieval; independent masked snippets | Completion similarity/retrieval metrics; no successive regression suite | Context selection diagnostics; requires an entirely new maintenance layer |
| [BigCodeBench](https://github.com/bigcode-project/bigcodebench) / [EvalPlus](https://github.com/evalplus/evalplus) | Function-level synthesis, including library use / expanded HumanEval and MBPP tests | Executable correctness tests; no evolving repository | Evaluator smoke tests and edge-case design; poor primary fit for document replacement |

## Four longitudinal options worth inspecting closely

### SlopCodeBench: the clearest controlled starting point

Gabriel Orlanski and colleagues' benchmark evaluates architecture choices as
specifications expand. The v2 paper uses fresh containers with persistent working
directories, and distinguishes strict success from current-checkpoint success
without regression tests. Unfinished checkpoints count as incorrect; structural
metrics exclude missing workspaces. Consequently, structural-quality averages can
describe a different set of outputs than correctness averages. These are useful
reporting distinctions, not measures of comment truth. [Paper v2, §§2.4–3](https://arxiv.org/html/2603.24755v2).

The [runner](https://github.com/SprocketLab/slop-code-bench#prerequisites) requires
Python 3.12+, Docker, and a model-access configuration. Problems now live in
[gabeorlanski/scb-problems](https://github.com/gabeorlanski/scb-problems), with
checkpoint specifications, static assets, reference solutions, and pytest tests.
Its README identifies `file_backup` as a worked example. The
[evaluation guide](https://github.com/SprocketLab/slop-code-bench/blob/main/docs/evaluation/README.md)
categorizes prior-checkpoint tests as regressions, but describes FUNCTIONALITY
tests as optional; the paper's strict correctness includes all tests. Pin the
actual scorer and choose the strict outcome explicitly rather than infer scoring
from that label.

**Adaptation judgment:** choose a few problems whose requirements support genuine
invariants, such as backup preservation and configuration precedence. Establish
the same verified initial implementation in every arm before measuring later
edits. Otherwise, differing first implementations change both code and comment
placement. Keep future specifications, reference solutions, and evaluator files
outside the agent workspace. Derive explanations from currently authorized
requirements, never from the next checkpoint's solution. New authored problems
using this format can reduce public-solution exposure while retaining a reusable
runner. That is more feasible than inventing a full benchmark framework.

### ChainSWE: the closest real-repository maintenance match

Qirui Jin and collaborators' `Seq` mode restarts the agent between bugs while
retaining its patches; `Seq+Mem` additionally preserves conversation history.
`Oracle` applies earlier gold fixes before each task. Sequences continue after
failures, allowing later repair. These distinctions directly separate repository
state from chat memory. Code overlap and test re-execution select candidate chains;
overlap is evidence of connected work, not proof that every later task requires
every earlier rationale. [Paper v2, §§3.2, 4.3](https://arxiv.org/html/2607.02606v2).

The [dataset card](https://huggingface.co/datasets/C-lister/ChainSWE/blob/main/README.md)
provides one row per chain, a shared starting commit/image, and ordered
`bug_fixes`; it directs evaluation to [Microsoft SWE-Edit](https://github.com/microsoft/SWE-Edit).
This gives a concrete import target instead of requiring historical issue mining
from scratch. The paper's Appendix A records patch, test-patch, F2P/P2P lists,
commands, and source benchmark identifiers for individual fixes.

**Adaptation judgment:** make `Seq` the natural first comparison. Preserve comment
or document changes alongside code, and separately snapshot acceptance tests so
that an agent cannot change its own grading. Check that the selected chain's
earlier requirements are rerun at each later step; a per-issue P2P list need not
cover every previously added behavior. Keep oracle continuation as a diagnostic,
clearly separate from unrepaired roll-forward performance. Because the corpus
reuses SWE-family assets, deduplicate train/pilot/held-out pools by underlying
repository and issue, not merely by the new chain ID. Select chains before seeing
which treatment wins.

### SWE-CI: useful adaptation dynamics, expensive causal ambiguity

Jialong Chen, Xander Xu, Hu Wei, Chuan Chen, and Bing Zhao describe base/target
pairs spanning substantial human history. The reported average 71 intervening
commits is provenance, **not 71 separately replayed agent tasks**. An architect
turns test gaps into requirements; the programmer updates the current code.
EvoScore weights normalized test progress over iterations, including regression
below baseline. It is a functional proxy for maintainability, not a direct
measurement of explanation quality. [Paper v4, §§2–3](https://arxiv.org/html/2603.03823v4).

The [official dataset card](https://huggingface.co/datasets/skylenage-ai/SWE-CI)
announces v2 on 2026-04-20, adding 126 tasks and a `default_v2` split of 100 tasks
from distinct repositories. Its lower description still says the full collection
contains 137 tasks; record exact split and IDs instead of deriving a current
total from these inconsistent statements. The release provides source archives,
metadata, and environment images. [Official trajectories](https://huggingface.co/datasets/skylenage-ai/SWE-CI-trajectory)
are available for inspection; their card warns that full evaluation is expensive.

**Adaptation judgment:** if inline comments improve an early patch, the architect
may then issue different later requirements. The experiment would estimate an
adaptive workflow effect, not simply a location effect under matched tasks.
Initially reuse environments and test deltas while fixing a reviewed requirement
sequence. Later, evaluate the adaptive loop as a separate condition, charging for
both agents. Record whether target tests or their information reach the programmer;
otherwise a test-derived explanation can silently become an answer channel.

### SWE-Milestone: realistic dependency structure, evaluator audit required

Gangda Deng, Zhaoling Chen, and collaborators reconstruct release history into
dependency graphs of milestones. The public harness supports continuous sessions,
captures checkpoints, and unlocks downstream work; setup uses separately versioned
data and container images. Its
[README and setup links](https://github.com/DeepCommit-ai/SWE-Milestone) describe
matching data/image versions and configurable agents. This is attractive for
cross-module constraints, but a session-reset treatment would be a deliberate
protocol modification. [Paper v4, §§3–4](https://arxiv.org/html/2603.13428v4).

Fei Ding's October 2026 primary audit reports unstated, non-inferable names or
paths in tests for 25 of 98 graded milestones in SWE-Milestone v1.0.2. It also
reports that removing affected tests leaves overall ranking comparatively robust;
the finding does not invalidate every milestone. This is an external audit, not
a local reproduction. [Audit v1, §§4–7](https://arxiv.org/html/2610.30635v1).

**Adaptation judgment:** review scored assertions against the available task
contract before creating factual annotations. If the inline inventory alone
supplies an otherwise hidden helper name, the treatment measures additional
specification information. Fix that problem for every arm. Defer this corpus
until smaller sequences establish that the runner, context audit, and accounting
work; multi-language environments and dependency graphs increase pilot cost.

## Supporting corpora and distinctions

SWE-EVO's release-to-release tasks are substantial: its v1 paper reports an
average of about 21 edited files and 874 tests per instance. But producing a patch
for a release delta does not itself test knowledge surviving fresh sessions.
Reuse its [released harness and task data](https://github.com/SWE-EVO/SWE-EVO)
for larger follow-up cases after constructing justified checkpoints; avoid
arbitrarily splitting a gold patch into artificial requirements.
[Paper v1, §3](https://arxiv.org/html/2512.18470v1).

Verified and Pro are distinct benchmark projects. The familiar Verified set is a
filtered part of SWE-bench; Scale's Pro sources different tasks. Pro's current
[V2 guide](https://github.com/scaleapi/SWE-bench_Pro-os/blob/main/v2/README.md)
specifies 642 tasks, an offline agent phase, sanitized history, and fresh-sandbox
regrading. Original public-set results with 731 tasks require the explicit `v1`
configuration. Pro's original 1,865 total included nonpublic subsets; it was never
1,865 freely downloadable evaluation tasks. [Scale's dataset design](https://labs.scale.com/leaderboard/swe_bench_pro).

OpenAI's February 2026 audit found flawed tests/descriptions in 59.4% of an
intentionally difficult 138-task Verified subset, and elicited memorized details
from tested models. That percentage is not an estimate for all 500 tasks. Public
benchmarks remain useful engineering fixtures, but matched treatment does not
remove contamination: a model remembering the fix may have little need for either
form of context. [Audit, background and contamination](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/).

Three context benchmarks must remain separate. SWE-ContextBench measures reuse of
related task experience; its [v1 abstract](https://arxiv.org/abs/2602.08316v1)
describes 300 base plus 99 related tasks, whereas its current repository describes
the larger release in the table. CTXbench belongs to the ETH Zurich/LogicStar
AGENTS.md study. Its [public harness](https://github.com/eth-sri/agentbench)
uses the older AGENTBench name and includes context-generation, execution,
evaluation, and cost-analysis stages. EuniAI's ContextBench instead supplies
gold-context retrieval annotations. Neither a retrieved trajectory nor an
instruction file is automatically equivalent to code-owned rationale.

For explanation maintenance, Panthaplackel, Nie, Gligoric, Li, and Mooney's
[ACL 2020 comment-update dataset](https://github.com/panthap2/LearningToUpdateNLComments)
provides real code/comment change pairs. Use it to seed stale-comment diagnostics,
with independent factual review; matching one human rewrite is not the same as
preserving the facts necessary for later edits. It does not supply matched external
documentation or multi-session repository outcomes.
[Paper, task and dataset](https://arxiv.org/abs/2004.12169).

## Two closer memory-specific benchmarks

**VibeMemBench** selects tasks where a reference memory configuration improved
resolution. Its 111 targets therefore describe a selected population, not ordinary
repository tasks. Held-out solvers show directional gains of 1.1–4.5 percentage
points for four of five models, but all five reported confidence intervals cross
zero; 11 of 12 tested memory systems do not outperform the no-memory baseline.
Retrieval occurs only initially, and solver token/step accounting excludes memory
construction and retrieval costs. Gold target patches enter offline candidate
screening, not runtime memory distillation. These distinctions matter for fair
reuse. [Paper v1, §§3–4, Tables 1–2](https://arxiv.org/html/2609.23570v1).

The [official artifact directory](https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/VibeMemBench)
was verified through GitHub's read-only API to contain README, LICENSE, scripts
and assets after the rendered page failed. Executability and content rights were
not audited. Reuse its experience comparisons while adding matched inline/external
facts, maintenance costs, and an independently selected task population.

**DreamBench-SWE** places useful knowledge in earlier sessions and removes it
from the final task prompt. The original hybrid-versus-verbatim contrast is null
(p=.518); successor v2.1.0 separates memory conditions from no memory without
establishing superiority between the memory systems. These are curated tasks
often requiring exact recall, not a representative longitudinal repository sample.
Its paper distinguishes the original and successor configurations.
[Paper v1, §§5.1, 6.2, 6.6, 8](https://arxiv.org/html/2608.20664v1).

The [official repository](https://github.com/iroiro147/dreambench-swe) provides
Apache-2.0 public fixtures and analysis; hidden oracles and reference solutions
are excluded. Public smoke runs therefore cannot reproduce the full experiment.
The inspected main tree identifies v2.0.5, with v2.1.0 successor release assets
separate. Reuse its session-boundary and stale-memory patterns with independently
authored hidden checks, rather than treating its restricted evaluator as a
ready-to-run primary benchmark.

## Artifact rights and practical limits

These are observed release declarations, not a legal determination. Repository
code licenses do not automatically relicense upstream source, tests, or datasets.
“Unknown” means not verified in this review; it does not imply permission or prohibition.

| Artifact | Harness/code license checked | Dataset/content declaration checked |
| --- | --- | --- |
| SlopCodeBench | [MIT](https://github.com/SprocketLab/slop-code-bench/blob/main/LICENSE) | Problem repository [LICENSE is Apache-2.0](https://github.com/gabeorlanski/scb-problems/blob/main/LICENSE), conflicting with README's MIT badge; resolve before redistribution |
| ChainSWE | [SWE-Edit MIT](https://github.com/microsoft/SWE-Edit/blob/main/LICENSE) | [Card says MIT](https://huggingface.co/datasets/C-lister/ChainSWE/blob/main/README.md); upstream asset rights require separate inventory |
| SWE-CI | [Apache-2.0](https://github.com/SKYLENAGE-AI/SWE-CI/blob/main/LICENSE) | [Card licensing section](https://huggingface.co/datasets/skylenage-ai/SWE-CI#licensing): metadata/curation Apache-2.0; source retains upstream licenses |
| SWE-Milestone | [MIT](https://github.com/DeepCommit-ai/SWE-Milestone/blob/main/LICENSE) | Separate dataset license not verified; upstream source remains separate |
| SWE-EVO | [MIT](https://github.com/SWE-EVO/SWE-EVO/blob/main/LICENSE) | Separate dataset license not verified |
| Verified / Pro | [SWE-bench MIT](https://github.com/SWE-bench/SWE-bench/blob/main/LICENSE) / [Pro MIT](https://github.com/scaleapi/SWE-bench_Pro-os/blob/main/LICENSE) | Verified card not verified; [Pro card](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro#license) explicitly retains upstream task-content licenses |
| SWE-ContextBench / CTXbench / ContextBench | First unverified; [CTX harness MIT](https://github.com/eth-sri/agentbench/blob/main/LICENSE); ContextBench README declares Apache-2.0 | [SWE-ContextBench card MIT](https://huggingface.co/datasets/jiayuanz3/SWEContextBench/blob/main/README.md); other dataset grants unverified; CTX paper Appendix D lists varied upstream licenses |
| RepoQA / CrossCodeEval / RepoBench | [Apache-2.0](https://github.com/evalplus/repoqa/blob/main/LICENSE) / [Apache-2.0](https://github.com/amazon-science/cceval/blob/main/LICENSE) / [CC-BY-4.0](https://github.com/Leolty/repobench/blob/main/LICENSE) | Separate dataset and upstream rights not verified |
| BigCodeBench / EvalPlus | [Apache-2.0](https://github.com/bigcode-project/bigcodebench/blob/main/LICENSE) / [Apache-2.0](https://github.com/evalplus/evalplus/blob/master/LICENSE) | Separate dataset grants not verified |
| Comment-update corpus | [Repository MIT](https://github.com/panthap2/LearningToUpdateNLComments/blob/master/LICENSE) | Separate upstream snippet rights not verified |

Most candidate execution paths use Linux containers. Compatibility with this
Windows workspace, image availability, actual disk consumption, and model adapter
behavior remain untested. A documented installation command is not evidence of a
working local setup. [BigCodeBench's repository](https://github.com/bigcode-project/bigcodebench) was marked archived when inspected;
pin and verify dependencies if using it as a small execution diagnostic.

## A practical first corpus

Propose a feasibility pilot of three or four SlopCodeBench problems and four to
six short ChainSWE chains, selected across task families and repositories before
outcome inspection. These numbers are an engineering pilot size, not a power
calculation. Select problems with independently explainable constraints and
nontrivial but attainable baseline performance for the weaker model. A corpus
where every arm fails cannot distinguish useful placement effects.

Reuse their test boundaries and workspace persistence; add a small shared manifest
of fact IDs, source provenance, applicable checkpoints, and code ownership. Build
both placements from that manifest. Use ContextBench's trace concepts to record
which facts are encountered, while recognizing that file visibility does not prove
understanding. Hold ordinary build instructions and tests constant. Preserve
failures and infrastructure costs, including context preparation and later repairs.
Keep fresh authored sequences for confirmation so public benchmark solutions are
not the only evidence. Full statistical design remains in the evaluation protocol.

## Search method and verification record

This was a targeted artifact review, not a systematic literature survey. Searches
combined benchmark names with `github`, `dataset`, `license`, and `continuous
evolution`; citation-following discovered SWE-Milestone and its recent evaluator
audit. Evidence above comes from versioned arXiv papers, author/project repositories,
official dataset cards, and the primary Verified audit. Secondary search results
were discovery leads only. GitHub's read-only license API was used to cross-check
repository LICENSE identification; no upstream issues or files were changed.
Follow-up searches for coding-agent memory benchmarks added VibeMemBench and
DreamBench-SWE; their selected methods, result sections, and artifact availability
were inspected, not their complete implementations.

Access date for every external link: **2026-11-05**. Paper versions and section
locators are named above. Repository `main` links are mutable inspection points,
not experiment pins; a runnable corpus must record commit SHAs, dataset revisions,
image digests, task IDs, and scorer configuration. Failed raw-card fetches for
Verified, SWE-EVO, and SWE-Milestone left their separate dataset licenses
unverified. The SWE-CI rendered card was accessible despite raw-card failures.
No reported external performance number is presented as a local result.
