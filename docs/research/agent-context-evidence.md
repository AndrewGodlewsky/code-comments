# Empirical evidence: comments as persistent context for coding agents

Research date: 2026-11-04. This is a targeted primary-source review, not a systematic literature review. Numeric claims were checked against the linked papers' methods, tables, or results. No experiments were rerun. Percentage-point changes below are distinguished from relative percentage changes.

The hypothesis under investigation is that selected comments preserving intent, constraints, and relationships can make successive changes more reliable, particularly for less capable models, and can replace some information currently kept in separate shared documents.

**Assessment:** There is causal evidence that correct, task-relevant comment content can help weaker models on bounded coding tasks. There is also controlled evidence of null effects and harm from misleading or irrelevant documentation. The reviewed literature does **not** establish that selectively maintained inline comments outperform equivalent separate documentation over long-running project evolution, or that this strategy makes a cheaper model as dependable as a stronger one after total authoring and maintenance costs. That remains a plausible, testable hypothesis.

## Evidence map

| Study and checked version | What was actually evaluated | Relation to the hypothesis |
|---|---|---|
| [Pan et al., *Talking to Itself While Coding*](https://arxiv.org/html/2609.09242v1), 2026-09-08; arXiv lists acceptance to Findings of EMNLP 2026 | Controlled comment-prefix interventions, principally single-shot competitive programming | Direct evidence for correct information transfer to weaker models; no persistent-comment maintenance |
| [Vitale et al., *On the Impact of Code Comments for Automated Bug-Fixing*](https://arxiv.org/html/2601.23059v1), 2026-01-30; accepted ICPC 2026 | Fine-tuning and inference ablations for repairing isolated Java methods | Direct comment ablation, but comments generated from the correct answer |
| [Macke and Doyle, *Testing the Effect of Code Documentation*](https://aclanthology.org/2024.findings-naacl.66.pdf), Findings of NAACL, June 2024 | Test generation from functions under documentation mutations | Null benefit on one outcome; incorrect documentation harmful |
| [Liu et al., *RepoQA*](https://arxiv.org/html/2406.06025v1), preprint, 2024-06-10 | Function retrieval from long repository code contexts | Counterevidence to a universal benefit from comments; retrieval only |
| [Song et al., *Code Needs Comments*](https://aclanthology.org/2024.findings-acl.809.pdf), Findings of ACL, August 2024 | Continued pretraining with comment-augmented code | Training-data evidence, not a repository annotation workflow |
| [Gloaguen et al., *Evaluating AGENTS.md*](https://arxiv.org/html/2602.11988v3), preprint first submitted 2026-02-12; checked revision 2026-09-29 | Real repository issue resolution with absent, generated, or developer-provided context files | Relevant comparison against global context, but no matched inline-comment arm |
| [Jin et al., *ChainSWE*](https://arxiv.org/html/2607.02606v2), preprint first submitted 2026-07-01; checked revision 2026-09-01 | Dependent bug-fix chains in cumulative repository state | Direct successive-edit evidence; no comment treatment |
| [Chen et al., *SWE-CI*](https://arxiv.org/html/2603.03823v4), preprint first submitted 2026-03-04; checked revision 2026-04-01 | Repeated requirement/implementation cycles toward a later repository state | Regression-sensitive evolution benchmark; no comment treatment |

## What the experiments support—and what they do not

### 1. Correct comment content can help a weaker model

Pan et al. inject stronger-model comment blocks into four weaker recipients. On the Gemini-source passing subset, Qwen3-8B pass@1 rises from **53.6% to 70.8%**; corrupting one substantive step reduces it to **48.2%**. Correct-to-corrupted decreases are significant for all four recipients after Holm correction. These are matched-subset results, not whole-benchmark rankings. [Tables 1–2](https://arxiv.org/html/2609.09242v1)

The intervention supplies solution knowledge. Most effects in the smaller repository-class replication do not survive multiplicity correction. Comments are generation prefills; persistent maintenance, lifetime costs, and long-term model-tier substitution remain untested. [Sections 4.1–4.2](https://arxiv.org/html/2609.09242v1)

### 2. Bug-fix improvements have an important oracle condition

Vitale et al. vary comments during fine-tuning and inference for CodeT5+ 220M and DeepSeek-Coder 1.3B. Comparing no-comments/no-comments with comments/comments, **exact match** rises from **3.26% to 9.80%** and **5.57% to 12.77%**, respectively. This measures reference-patch agreement, not execution-based bug resolution. [Table 3](https://arxiv.org/html/2601.23059v1)

GPT-3.5 generated replacement comments from **fixed methods**, then supplied them with buggy inputs. The authors acknowledge this oracle condition is unavailable before fixing. Results establish an upper bound, not practical gains from existing comments. Tasks are isolated Java methods, filtered to 512 tokens. [Sections 4.1–4.2](https://arxiv.org/html/2601.23059v1)

### 3. Useful documentation does not improve every outcome

Macke and Doyle have GPT-3.5 and GPT-4 generate unit tests from HumanEval functions, varying docstrings, missing lines, unrelated docstrings, and identifier names. Correct documentation produces no significant improvement in successful-test proportion; some coverage comparisons improve. Incorrect documentation significantly worsens performance. [Results and discussion, pp. 1046–1048](https://aclanthology.org/2024.findings-naacl.66.pdf)

This tests a proxy for model understanding, not human comprehension or maintenance. Functions are self-contained; documentation may repeat recoverable information. The authors flag potential HumanEval contamination. The null does not settle whether otherwise unavailable domain constraints help. [Methods and limitations](https://aclanthology.org/2024.findings-naacl.66.pdf)

### 4. Comments can obstruct long-context retrieval

RepoQA v1 contains 500 function-search tasks from 50 repositories in five languages. At a 16K code-context setting, removing natural comments improves several models: GPT-4o goes from **90.6% to 93.2%** and DeepSeek-Coder-33B from **48.4% to 75.4%**. Gemini-1.5-Flash instead drops from **90.0% to 54.2%**. [Table 1 and evaluation](https://arxiv.org/html/2406.06025v1)

Removal substitutes synthetic line-number comments to preserve positions and context size. Gemini sometimes continues the numbering instead of answering, complicating interpretation. This demonstrates sensitivity to context construction, not universal comment harm. Retrieval neither edits code nor tests constraint preservation. [Section 4](https://arxiv.org/html/2406.06025v1)

### 5. Training on comments is a different intervention

Song et al. compare continued pretraining on original, comment-free, and generated-comment corpora. For CodeLlama-7B on matched filtered source samples, comment augmentation raises HumanEval pass@1 from **33.54% to 39.02%**, while MBPP falls from **44.80% to 43.00%**. The full study reports several model/dataset combinations rather than a universally positive effect. [Table 5](https://aclanthology.org/2024.findings-acl.809.pdf)

This investigates alignment during training, not adding repository comments at inference time. Augmentation, filtering, pretraining, and instruction tuning must be distinguished; a combined recipe does not establish benefits from inline placement or persistent memory for a fixed deployed model. [Sections 3–4](https://aclanthology.org/2024.findings-acl.809.pdf)

### 6. Repository context files change behavior without proven general success gains

Four agent/model pairs solve 300 SWE-bench Lite and 138 CTXbench tasks. Generated files change resolution by **−0.5 and −2 percentage points**, neither significant (**p=.87, .37**). Developer files average **+2.4 points** versus none, nonsignificant (**p=.21**), but outperform generated files (**p=.038**). Generated-file costs rise **20% and 23%**. [Sections 4.1–4.2, Tables 2–3](https://arxiv.org/html/2602.11988v3)

A documentation-removal ablation yields +2.7 points for generated files. This suggests redundancy matters. Equivalent inline placement, later regressions, and documentation drift are untested. Claims of proven accuracy harm overstate these statistics. [Appendix B and limitations](https://arxiv.org/html/2602.11988v3)

### 7. Carrying state forward is measurably different from isolated fixing

ChainSWE constructs 100 chains containing 304 bugs across 54 Python repositories, averaging 3.04 bugs per chain. It compares oracle prior fixes, accumulated model patches with fresh conversations, and accumulated patches plus conversation history. Across seven models and three context-management configurations, per-bug accuracy is **58.9%, 36.5%, and 36.9%**, respectively. [Sections 3–5](https://arxiv.org/html/2607.02606v2)

Transcript preservation has little aggregate benefit. Chains are short and selected for individual tractability. Oracle resets also replace imperfect code, so the gap is not exclusively forgetting. No arm stores selected intent in comments or compares it with documentation. [Methods and results](https://arxiv.org/html/2607.02606v2)

### 8. Evolution benchmarks expose regressions, but do not validate comments as the remedy

SWE-CI uses 100 repository tasks derived from development spans averaging 233 days and 71 commits. An architect generates requirements from test gaps; a programmer modifies the persistent codebase, with up to 20 cycles. Across 20 models, most have a **zero-regression rate below 25%**; only two Claude Opus models exceed 50%. [Sections 3–4](https://arxiv.org/html/2603.03823v4)

Historical age describes source material, not deployment duration. Iterations approach a target state, not every human request. An architect mediates requirements, complicating attribution. This exposes regressions but supplies no comment/doc placement ablation or evidence that comments prevent them. [Protocol and results](https://arxiv.org/html/2603.03823v4)

## Where the evidence stops

These evidence types answer different questions:

| Evidence type | What it can establish | What it cannot establish alone |
|---|---|---|
| Human comprehension experiments | Effects on human reading, recall, or change performance | Effects on LLM agents or model-tier substitution |
| Training-data experiments | Effects of changing learned weights | Benefits of adding comments to an existing project |
| Single-shot comment interventions | Causal effects of supplied information under a fixed task | Durability, freshness, discovery, or maintenance economics |
| Repository issue-resolution experiments | Navigation and patch success in realistic code context | Reliability of future edits to an agent-modified repository |
| Sequential maintenance benchmarks | Accumulation, regression, recovery, and context-history effects | Effectiveness of an untested comment policy |

The critical untested link is **durable, accurately maintained information → repeated discovery and correct use → fewer downstream regressions at lower total cost**. This is an inference about the missing experiment, not a reported result. None of the eight studies directly compares equivalent intent/constraint information in inline comments and separate shared documents over successive agent edits. Likewise, none establishes whether a local annotation preserves cross-file relationships better than a maintained design document.

## Requirements for a useful next experiment

The [proposed evaluation protocol](evaluation-protocol.md) develops the experiment. These are the requirements most directly motivated by the evidence above; they are research-design inferences, not demonstrated benefits of a comment policy.

- Generate annotations only from information available before the task. Correct-answer-derived comments belong in a separately labeled upper-bound condition.
- Compare identical facts beside code and in separate documentation. Record discovery and actual inclusion in context before interpreting a placement advantage.
- Preserve cumulative repository state. Distinguish regressions caused by prior incorrect code from failures to recall earlier information.
- Establish within-model effects before claiming a weaker model can substitute for a stronger one. Measure uncertainty and consistency across repeated trajectories.
- Include stale and conflicting annotations, then evaluate the cost and reliability of keeping comments current.
- Count authoring, review, updates, inference, and recovery work across the whole trajectory. A first-task gain does not establish lifetime savings.

The research supports testing accurate information that code alone does not express. Placement, persistence, model substitution, and cost savings remain open variables; the evidence does not yet select an annotation taxonomy or skill workflow.
