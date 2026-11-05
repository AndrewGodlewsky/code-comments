# What comment experiments actually establish

Research checked on **2026-11-05**. This extends [the initial evidence map](agent-context-evidence.md). It is a targeted primary-source review, not a systematic review or a reproduction. **No model experiments were rerun.** Effects below are reported results; percentage points (pp) and relative percentages are distinguished.

Accurate comments can improve bounded code-generation and repair tasks, including tasks performed by small models. The stronger claim remains unproven in the studies examined here: that an agent can preserve useful rationale through successive changes, retrieve it reliably, and make cheaper models competitive with stronger models at lower total cost. None of this report's direct comment experiments compares equivalent information in inline comments and accessible external documents throughout project evolution. The [related-systems report](related-systems-and-researchers.md) separately covers memory systems and external rationale tools.

## Keep five different questions separate

| Question | Evidence found | Remaining uncertainty |
| --- | --- | --- |
| Does accurate additional information help? | Controlled comment interventions and interactive correction show benefits. | Which naturally available facts provide the benefit? |
| Does inline placement help? | Comment prefixes, interleaved generation, and retrieval ablations test particular representations. | Equal facts, retrieval opportunities, and token budgets across inline/external conditions. |
| Can a smaller model benefit? | Several studies include 220M–9B models. | Reliability and economics against a stronger model on repeated maintenance. |
| Can comments stay correct? | Inconsistency datasets and repair systems exist; repairs remain imperfect. | Maintaining rationale and cross-file contracts through a trajectory. |
| Can comments replace documents? | Repository-context experiments test some external files. | Selective replacement without losing global information or navigation. |

These are distinctions for interpreting evidence, not measured conclusions about Code Comments. Source comments and docstrings are also different from **pull-request review comments**: the latter are feedback conversations, not necessarily persistent annotations a future agent reads. Search hits about review-comment generation were excluded from direct-effect evidence. Likewise, good generated prose, high text-similarity scores, and successful future code changes are different outcomes.

## Direct interventions: useful information, with important conditions

### Pan and colleagues: strong evidence for correct solution hints

Dangfeng Pan, Zhensu Sun, Cenyuan Zhang, David Lo, and Xiaoning Du study 88 models observationally on LiveCodeBench v6 (1,055 problems) and intervene on four weaker recipients using three stronger sources. Checked **arXiv 2609.09242v1**, September 8, 2026; its [metadata](https://arxiv.org/abs/2609.09242v1) reports Findings of EMNLP 2026 acceptance. [§3.1; Appendix D.13](https://arxiv.org/html/2609.09242v1#S3.SS1).

On the Gemini-source passing subset, Qwen3-8B moves from **53.6% to 70.8% pass@1** with source comments; corrupting a substantive step reduces it to **48.2%**. All four correct-to-corrupted decreases survive Holm correction. This matched-subset intervention supports content correctness, not comment density. Source-pass filtering uses test outcomes; it is not an operational recipe for identifying trustworthy hints before solving a task. [§4.1, Tables 1–2](https://arxiv.org/html/2609.09242v1#S4.SS1).

The repository-class replication covers 61 C# and 130 Java tasks. Java has a positive pooled result, but only the Qwen wrong-topic cell survives individual multiplicity correction. These are generation prefills, without comment aging or subsequent maintenance. [§4.1, Table 3](https://arxiv.org/html/2609.09242v1#S4.SS1).

The paper claims a code/data release; its [artifact README](https://github.com/pdfCN/What-Makes-Comments-Help-Code-Generation) still describes a data release and future code release. Runnable reproduction was not verified.

### Vitale and colleagues: repair gains include answer-derived information

Antonio Vitale, Emanuela Guglielmi, Simone Scalabrino, and Rocco Oliveto evaluate CodeT5+ 220M and DeepSeek-Coder 1.3B. Checked **arXiv 2601.23059v1**, January 30, 2026; [metadata](https://arxiv.org/abs/2601.23059v1) reports ICPC 2026 acceptance.

Their Java-method corpus begins with 116,372 bug/fix pairs before further filtering; augmented instances exceeding 512 tokens are excluded. GPT-3.5 generates five comment categories from the **fixed method**, then supplies those comments with the buggy input. This supplies otherwise unavailable target behavior. [§4.1](https://arxiv.org/html/2601.23059v1#S4.SS1).

Holding no-comment fine-tuning fixed, adding inference comments increases exact match **3.26%→3.73%** and **5.57%→7.90%**. Changing both fine-tuning and inference yields **9.80%** and **12.77%**. Thus the large headline gain cannot all be attributed to a deployment-time annotation skill. Exact match measures reference-patch agreement, not execution-based resolution. [§5.1, Table 3](https://arxiv.org/html/2601.23059v1#S5.SS1).

The authors' negative control generates comments from buggy code instead: results are unchanged or slightly worse, including CodeT5+ **3.26%→2.92%**. This directly limits the inference that automatically explaining existing code supplies useful repair knowledge. [§6.1](https://arxiv.org/html/2601.23059v1#S6.SS1). The [Zenodo package](https://zenodo.org/records/17408251) is a replication lead, not a verified runnable setup here.

### PInG: editable comments can carry human correction

Yifeng Di and Tianyi Zhang's **ICSE 2025** PInG combines code generation, comment generation, human edits to comments, and code refinement. Checked [arXiv 2505.07768v1](https://arxiv.org/html/2505.07768v1), May 12, 2025; [official artifacts](https://github.com/NecoraNyaru/PInG) confirm venue and expose training/evaluation scripts.

The simulated-user experiment covers 164 HumanEval and 142 sampled sanitized MBPP tasks. An author supplies corrective feedback; annotators reconcile edits. Code-davinci-002 HumanEval pass@1 rises **46.3%→63.4%**, a **17.1 pp** gain. This is informed interactive correction, not autonomous preservation of existing context. [§IV-A–B; Table II](https://arxiv.org/html/2505.07768v1#S4).

In the 12-participant user study, **10/12** succeed with PInG versus **8/12** with Copilot; mean completion times are **14.65 versus 16.37 minutes**. That is **+16.7 pp success** and approximately **10.5% faster**. The abstract reverses these labels; use the results section and table. Small samples and different interaction workflows limit attribution to placement alone. [§VI-E, Figure 4, Table VII](https://arxiv.org/html/2505.07768v1#S6.SS5). It offers a concrete interface precedent, without a longitudinal document-replacement trial.

## Negative and mixed results constrain the hypothesis

### Documentation can change coverage without improving successful tests

William Macke and Michael Doyle's [Findings of NAACL 2024 paper](https://aclanthology.org/2024.findings-naacl.66.pdf), checked proceedings version, tests GPT-3.5/GPT-4 unit-test generation from HumanEval functions. Conditions remove docstrings, retain fractions, substitute unrelated docstrings, or change identifiers. Correct documentation produces **no significant difference in successful-test proportion** versus no documentation, although average line coverage improves. Unrelated documentation significantly increases failures/runtime errors; reported successful proportions are **22.1% and 68.1%** for the two models. [§§4–6, pp.1045–1048, Figures 2–5].

This is a model-understanding proxy, not bug fixing. Redundant function descriptions and possible benchmark contamination constrain generalization. It is evidence against assuming every accurate comment adds useful knowledge, while the coverage result prevents flattening the study into “comments do nothing.”

### RepoQA shows that more natural-language context can hinder retrieval

Jiawei Liu and colleagues' [RepoQA](https://arxiv.org/html/2406.06025v1), checked **v1, June 10, 2024**, tests 500 function-search tasks from 50 repositories across five languages. In its 16K context experiment, comment removal changes retrieval accuracy **48.4%→75.4%** for DeepSeek-Coder-33B and **90.6%→93.2%** for GPT-4o; Gemini-1.5-Flash changes **90.0%→54.2%**. [§§3–4, Table 1].

The removal condition inserts synthetic line-number comments to preserve positions and approximate context size. Gemini sometimes continues that numbering, confounding a simple interpretation of natural comments' value. Retrieval is neither editing nor constraint preservation. The relevant warning is that context construction and model-specific behavior must be measured, including whether the annotation helps locate the owner or distracts from it.

### External context files are not a proven general accuracy improvement

Thibaud Gloaguen, Niels Mündler-Sasahara, Mark Niklas Müller, Veselin Raychev, and Martin Vechev's [*Evaluating AGENTS.md*](https://arxiv.org/html/2602.11988v3) was checked at **v3, September 29, 2026**; preprint status in the [record](https://arxiv.org/abs/2602.11988v3).

Four agent/model pairs solve 300 SWE-bench Lite and 138 CTXbench tasks. Generated files change average resolution by **−0.5 pp** and **−2 pp** (p=.87, .37); developer files average **+2.4 pp** versus none (p=.21). Generated files increase costs **20%/23%**. Developer files outperform generated files (p=.038). [§4.2, Tables 2–3].

Removing other documentation after file generation yields **+2.7 pp** for generated files, consistent with redundancy as an explanation, but not an isolated placement test. [Appendix B, Figure 12]. “Proven accuracy harm” overstates the main statistics. No matched inline condition or evolving-file maintenance condition is present. The study supports measuring useful new information and downstream cost separately from instruction compliance.

## Small-model training results do not establish a repository workflow

### MANGO separates comment prompting from comment-aware training

Yijie Chen, Yijin Liu, Fandong Meng, Yufeng Chen, Jinan Xu, and Jie Zhou's **Findings of ACL 2024** [MANGO paper](https://aclanthology.org/2024.findings-acl.420.pdf), checked proceedings version, evaluates StarCoder-7B and WizardCoder-3B/7B on 164 HumanEval and 500 MBPP problems, sampling ten outputs per problem. It combines comment-contrastive fine-tuning with prompting for logical comments. [§§3–4, pp.7042–7044].

Table 3 is mixed at pass@1: StarCoder-7B improves **35.93→39.73** on HumanEval but drops **42.79→40.92** on MBPP; WizardCoder-7B improves **52.80→54.59** and **42.73→46.91**. Prompting alone is a separate arm. Its comments-versus-external-reasoning comparison concerns generated intermediate reasoning and training loss, not maintained documents supplied to a future agent. [Tables 1–3, pp.7042–7044].

The [released implementation](https://github.com/pppa2019/Mango) is a precedent for small-model adaptation. It does not justify requiring a deployed model to comment more, nor treating improvements at pass@10 as improvements at pass@1.

### Code Needs Comments concerns learned weights

Demin Song, Honglin Guo, and collaborators at Shanghai AI Laboratory, Fudan, and CUHK evaluate comment augmentation for continued pretraining in [*Code Needs Comments*](https://aclanthology.org/2024.findings-acl.809.pdf), **Findings of ACL 2024**, checked proceedings version. The intervention includes corpus filtering and model-generated annotations. For CodeLlama-7B, Table 5's matched filtered source conditions change HumanEval pass@1 **33.54%→39.02%**, while MBPP changes **44.80%→43.00%**. [§§3–4; Table 5, p.13646].

This supports investigating code–language alignment during training. It supplies no estimate of the benefit of adding comments to a fixed model's repository at inference, and the mixed benchmark result matters when interpreting broad claims of improvement. Training costs also belong to any comparison with a comment-authoring skill.

## Keeping explanations accurate is a separate empirical problem

### Real histories contain stale rationale, not only stale summaries

Fengcai Wen, Csaba Nagy, Gabriele Bavota, and Michele Lanza's **ICPC 2019** [author manuscript](https://www.inf.usi.ch/lanza/PUBS/P/Wen2019a.pdf) mines approximately **1.3 billion AST changes across 1,500 Java systems** and manually examines **500 commits**. Its taxonomy includes obsolete implementation rationale, delayed comment corrections after refactoring, and outdated technical-debt comments. Some rationale is removed after its justification ceases to apply. [§§III–IV, especially IV-B, PDF pp.7–8].

This observational, keyword-selected evidence does not estimate a causal bug reduction from comments; unchanged comments need not be wrong. It does show why proximity alone cannot be assumed to preserve truth. Keeping reasons beside code still requires tracking when the reason's prerequisites change, including dependencies outside the annotated method.

### Learned comment updates are feasible but similarity can mislead

Sheena Panthaplackel, Pengyu Nie, Milos Gligoric, Junyi Jessy Li, and Raymond Mooney's [ACL 2020 paper](https://aclanthology.org/2020.acl-main.168.pdf), checked proceedings version, learns edits to existing comments from code changes mined from project histories. The reranked edit model reaches **18.433% exact match**. Simply copying the old comment scores **46.218 BLEU-4**, despite never updating it. [§6.1, Table 2, p.1859].

The result illustrates both an available maintenance approach and a measurement trap: a nearly unchanged but incorrect sentence can resemble the human reference. It motivates checking the changed factual claim and its effect on a subsequent task, not choosing a policy solely by BLEU or fluent prose. This is a comment-update experiment, not evidence of improved downstream coding.

### C4RLLaMA exposes incomplete repair and a reporting inconsistency

Guoping Rong, Yongda Yu, Song Liu, Xin Tan, Tianyi Zhang, Haifeng Shen, and Jidong Hu's **ICSE 2025** study fine-tunes CodeLLaMA-7B for inconsistency detection and rectification. Checked [institution-hosted manuscript](https://people.cs.umass.edu/~brun/class/2024Fall/CS692P/idllm.pdf) and [conference record](https://conf.researchr.org/details/icse-2025/icse-2025-research-track/10/Code-Comment-Inconsistency-Detection-and-Rectification-Using-a-Large-Language-Model).

Human-rated repair results are **55.9% and 65.0%**, but the abstract and §IV-E.2 assign these percentages to opposite just-in-time/post-hoc conditions. This review does not choose a label. The discussion identifies rewording that leaves the semantic error intact and cases needing external requirements. [§IV-E.2, Table VIII, Figure 3, PDF pp.8–9].

The [artifact repository](https://github.com/aiopsplus/C4RLLaMA) provides a research starting point. These results cannot establish reliable unattended synchronization; nor can code consistency alone decide whether code violated the requirement or the comment became obsolete. That choice needs an independent statement of intended behavior.

### Stale or defective annotations can transmit the wrong behavior

Zhikun Xia, Yuan Huang, Xiangping Chen, and Zibin Zheng's **ASE 2026** *When Comments Mislead* is directly relevant: its [official abstract](https://conf.researchr.org/details/ase-2026/ase-2026-research-track/29/When-Comments-Mislead-An-Empirical-Study-of-Outdated-Comments-in-LLM-Based-Code-Comp) reports completion biased toward historical implementations under outdated comments, with variation by signature length and task complexity. **Abstract-only evidence here:** the linked publisher DOI was inaccessible, and no open full manuscript surfaced in the searches. Sample size, effect sizes, and controls remain unverified. Treat it as a priority follow-up, not quantitative confirmation.

Yuan Huang, Yukang Zhou, Xiangping Chen, and Zibin Zheng's [*Comment Traps*](https://arxiv.org/html/2512.20334v2), checked **v2, February 18, 2026**, reports FSE 2026 acceptance in its [record](https://arxiv.org/abs/2512.20334v2). It inserts defective **commented-out code** into 1,000 Python completion contexts; Copilot/Cursor with GPT-4o/Claude 3.5 Sonnet are scored with CodeQL. The maximum **58.17% is a relative increase in flagged defects**, not a defect rate; average relative increases exceed 20% across the tested tool/model combinations. [§4; §5.1, Table 3]. This is a distinct annotation category from explanatory rationale, with static-analysis limits and deliberately injected defects. [Artifacts](https://github.com/da-da-di/CO-Code) are available; no reproduction was attempted.

## What would change the project's conclusion?

The following are **research-design inferences**, not established results or a chosen product policy. They complement the [evaluation protocol](evaluation-protocol.md).

First establish whether available knowledge improves future changes at all. Have a writer record facts available before the task, and give a fresh maintainer that context. Keep answer-derived summaries as a separately labeled upper bound. A positive upper bound with a failed practical writer would locate the problem in acquisition or fidelity rather than placement.

Then move identical factual content between comments and external documents. Record whether it was found, read, and acted upon. Equal delivery tests representation/use; normal repository navigation tests discoverability as well. Neither comparison alone answers both questions. Include code/tests-only, accurate, redundant, stale, and conflicting information conditions.

Carry both code and annotations forward across changes, including a retired workaround and an altered cross-file contract. Score downstream regressions and unsupported rationale, as well as comment corrections. A policy that makes comments agree with a buggy implementation must not receive full credit for consistency. Count authoring, review, retrieval, repair, and recovery costs throughout.

Finally compare model tiers within the same harness and budgets. Parameter count alone is not capability: training, tools, and baseline task success differ. The hypothesis should weaken if gains disappear under equal information, if they rely on privileged answer knowledge, if stale context causes net harm, or if total cost exceeds using the stronger model directly. A null placement result could still support preserving valuable knowledge externally; it would reject the specific inline advantage.

## Search method, verification, and remaining access limits

Searches on November 5, 2026 began from the repository's two empirical reports, followed paper references and artifact links, and used general web search with queries including `code comments LLM empirical study comments removal inconsistent code generation`, `code comments smaller language models rationale maintenance docstrings ablation study`, `code comments inconsistency LLM comment updates benchmark empirical`, `"When Comments Mislead" outdated comments paper`, and exact titles for venue verification. Primary evidence came from arXiv versioned full text, ACL proceedings, author/institution manuscripts, official conference records, and author repositories. Secondary summaries were discovery aids only.

Selection prioritized controlled effects on coding models, small-model contrasts, and comment drift/repair. It is not an exhaustive census, did not perform database-wide deduplication, and cannot establish that no qualifying experiment exists. Human evidence remains separately summarized in [comment maintenance and evaluation](comment-maintenance-and-evaluation.md); human comprehension findings do not transfer automatically to agents. Recent memory-system studies are handled in the related report rather than counted as inline-comment experiments.

The three key 2026 citations and numerical comparisons in the initial map survived primary-source checking. New qualifications concern inference-only versus joint training gains, sparse per-cell repository replication, source-internal reporting inconsistencies, and incomplete artifact availability. Repository landing pages were inspected; installations, training, evaluation scripts, and licenses of underlying datasets were not audited. Publication acceptance reported by arXiv metadata is identified as such. No evidence here verifies a working Code Comments skill or a maintained-comment advantage over equivalent external documentation.
