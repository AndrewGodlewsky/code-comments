# Subagent findings and review records

Visible subagent reports from the source research, five paper reviews, independent candidate review and final audit. These are historical records, not instructions governing the destination project.

## /root/candidate_review_14

Chat ID: 01a1af3f-b97f-7892-b95e-d0252d972dc7

### commentary

I’ll independently check the published candidate against issue #14’s acceptance criteria, including the research artifacts and repository checks.

### commentary

I’m using the code-review skill to check scope and repository standards separately. The candidate contains only the requested transcript and research collection; I’m now checking the evidence behind the summaries and artifact links.

### commentary

The repository check passed all 90 tests. The transcript matches its earlier published Git blob exactly, and all four PDF hashes match the README. The summaries checked so far accurately distinguish the papers’ findings from practical interpretations.

### final_answer

APPROVE — no blocking findings.

Reviewed tuple:

- Candidate: `e530286fff245ba3b14eeb05c9fc4e1d61df35ac`
- Target: `61b0cf5c9071c2ae9c43a47d898b81a6f14ce995`
- Issue #14: acceptance criteria revision 2
- Reviewer: `/root/candidate_review_14`

Independent evidence:

- Remote candidate and main refs match the tuple; GitHub issue body confirms revision 2.
- Required repository check passed: **90 tests, zero skipped**, exit 0.
- Transcript Git blob remains `d9123aaa1c536298817f804847eff649a4053c9f`, identical to published `31e7aa3`.
- All four committed PDFs match working-tree original download bytes and README SHA-256 values; page counts are 7, 21, 13 and 25.
- All **98 local links** and **56 PDF page targets** validated.
- All six HTML pages load offline in Brave at **1200px and 375px**, stylesheet loaded, no page overflow or browser errors.
- Factual comparisons against all four local PDFs support the summaries’ principal methods, metrics and limitations. The fifth brief consistently declares its abstract-only evidence.
- Standards and spec reviews found no blockers. Only assigned paths changed; final checkout is clean.

Original PDFs were not independently downloaded again. Browser verification here was automated layout/runtime inspection; coordinator supplied earlier screenshot inspection evidence.

Approval covers the candidate merge gate. Integration, cleanup and independent final audit remain required before closing #14; #7 and #2 must remain open.

### commentary

I’ll audit the merged state, CI results and cleanup evidence before issue #14 is closed.

### final_answer

PASS — post-cleanup audit for merged SHA `a0f6852788fb1c755a4e44dc2e263f821baacffe`.

Independently verified:

- PR #15 is merged; local and remote `main` match the merged SHA.
- Reviewed candidate `e530286fff245ba3b14eeb05c9fc4e1d61df35ac` is an ancestor; candidate-to-merge tree diff is empty.
- Combined-tree check log reports **90 tests passed** and repository checks passed.
- GitHub run `42166619185` completed successfully; both `check` and `windows-account` passed against the merged SHA.
- Local and remote task branches are absent. Only the clean primary checkout remains, on `main`.
- Integrated candidate content remains reachable; research and Python caches remain present. No evidence of lost unique work.
- Issues #7 and #2 remain open. Issue #14 remains open pending this verdict.

No blockers. Record this audit as `/root/candidate_review_14`, then close #14 and verify its closed state.

## /root/review_self_comments

Chat ID: 01a1af37-1a42-7070-b5e6-cdd052610ae7

### commentary

I’m using the PDF skill to check the full paper, including its experimental setup and appendices, before writing this review.

### commentary

The strongest evidence comes from changing the content of the same comment block: corrupting one algorithmic commitment removes its benefit. I’m also qualifying the paper’s repository result, where pooled comparisons are stronger than the individual model results.

### final_answer

Created [full-text review](A:/Claude/Book-connect/docs/research/ai-code-comments/2026-talking-to-itself-while-coding-summary.html), approximately 1,162 words.

Verified all 25 PDF pages. Key distinctions:

- Correct external hints: +17.2 percentage points, not relative percent.
- Source-success subsets: 757/892/870 problems.
- Repository replication: pooled support; only one individually significant comparison.
- Self-prompting’s 24% recovery compares different subsets/baselines.
- Experiment dates are unreported; 8 September 2026 is the preprint date.

HTML parsed successfully; local PDF and page targets checked. Shared-CSS visual verification remains with root.

## /root/review_bugfix_comments

Chat ID: 01a1af37-4af8-79a3-8cd1-06bbcb8c89f0

### final_answer

Created [the HTML review](A:/Claude/Book-connect/docs/research/ai-code-comments/2026-impact-of-code-comments-on-bug-fixing-summary.html).

Verified against the full local PDF:

- Main 220M/1.3B models, all eight EM results, and reported 11,637 test denominator.
- Fixed-code comment generation versus unsuccessful buggy-code follow-up.
- Retrained no-“how” ablation and supplementary GPT-4.1 result.
- Exact-match limitations and noncausal SHAP interpretation.
- Publication date distinguished from unreported execution dates.

Flagged the paper’s inconsistent filtering/split totals. HTML nesting and local links pass; no scripts or external runtime dependencies. Shared Brave visual verification remains with root.

## /root/review_comment_traps

Chat ID: 01a1af37-7acf-7b23-9b86-8b01ca8fdfdd

### final_answer

Created [2025-comment-traps-summary.html](A:/Claude/Book-connect/docs/research/ai-code-comments/2025-comment-traps-summary.html), approximately 1,121 words with 13 PDF page citations.

Verified:
- 1,000 Python samples, eleven placements, two tools × two models.
- 58.17% is relative increase: 416 → 658 defects.
- Ignore-comment prompting sometimes restored baseline; Cursor/GPT-4o reached 390 versus Blank’s 426.
- Tool versions and December 2025/FSE 2026 publication context.

Uncertainties explicitly addressed: experiment dates and model snapshots unreported; CodeQL coverage; no reported confidence intervals; speculative mechanisms; inconsistent prevalence counts. Browser QA remains for your collection-wide pass.

## /root/review_documentation

Chat ID: 01a1af39-4419-7392-b0dd-c07d49234aba

### commentary

I’m reading the full documentation paper and checking its tables, with particular attention to what the test-generation results do—and don’t—say about useful comments.

### commentary

I’m using the writing and information-hierarchy skills to put the key qualification first: correct comments improved line coverage even though they did not significantly improve test pass rates. The paper reports GPT-3.5 and GPT-4, but no dated API snapshots or experiment dates.

### final_answer

Created [the documentation review](A:/Claude/Book-connect/docs/research/ai-code-comments/2024-code-documentation-and-llm-understanding-summary.html), 927 words.

Verified all seven PDF pages, numerical results, model/date reporting, ACL metadata, local links, and table wrappers. Distinguishes coverage gains from pass-rate findings and identifier changes from comment changes.

Browser rendering remains for the parent’s shared Brave QA. Only the assigned file changed.

## /root/review_stale_comments

Chat ID: 01a1af3a-0956-7591-ab57-c7baca4f601c

### commentary

I’ll check the primary sources and write an explicitly limited evidence brief, keeping the missing methodology and model details visible.

### commentary

The sources agree on the central finding, but neither identifies the tested models or gives effect sizes. The brief separates those reported findings from unanswered methodology questions and suggested local checks.

### final_answer

Created [limited evidence brief](A:/Claude/Book-connect/docs/research/ai-code-comments/2026-when-comments-mislead-summary.html), 564 words.

Verified primary abstract and author announcement; full text remains unavailable. Source-derived material stays below 200 words per source, with no substantive direct quotations. Local links resolve; no JavaScript or CDN dependencies. No other files changed.

## /root/comment_research

Chat ID: 01a1af31-17f0-76b0-8e35-fda9e5835edb

### final_answer

Verified findings you can use immediately:

1. **[Comment Traps](https://arxiv.org/html/2512.20334v1)**, December 2025 preprint. Controlled completion experiments on **1,000 Python samples** from GitHub: remove a defective snippet, then reinsert it as commented-out code at 11 positions; compare against blank and length-matched nondefective-commented-code controls. Tested **GPT-4o and Claude 3.5 Sonnet**, each through **Copilot 1.257.0 and Cursor 0.44.11**. CodeQL measured reintroduced defects. **58.17% means relative increase**, not defective-output rate: Copilot/Claude produced **416/1,000** defective outputs without insertion versus **658/1,000** with defective code three lines below completion—**+24.2 percentage points / +58.17% relative**. Mean relative increases across positions were approximately 21–25%. Limitations: deliberately constructed contexts, old models/tool versions, static-analysis outcomes, and **commented-out executable code rather than prose comments**. This supports deleting obsolete code blocks, not deleting useful documentation.

2. **[When Comments Mislead](https://conf.researchr.org/details/ase-2026/ase-2026-research-track/29/When-Comments-Mislead-An-Empirical-Study-of-Outdated-Comments-in-LLM-Based-Code-Comp)**, ASE 2026, Zhikun Xia et al., DOI **10.1145/3832783.3834359**. Official conference abstract explicitly reports outdated comments biasing completions **toward historical implementations**, yielding plausible code that fails where implementation changed. Effects vary with signature length and task complexity. **Only the primary abstract was accessible**; no verified sample sizes, model identities, or effect sizes. Useful corroboration directly about stale prose, but do not attach numeric claims or portray its methodology as independently examined.

3. **[Are Prompt Engineering and TODO Comments Friends or Foes?](https://homepages.dcc.ufmg.br/~figueiredo/disciplinas/papers/icse2024obrien.pdf)**, ICSE 2024. **380 developer TODO cases, 1,140 Copilot generations**, comparing docstring-only, docstring+TODO, and docstring+TODO with “TODO” removed. Symptoms were reproduced in **35.36%** of TODO-included cases. Modified-TODO generation addressed **99 cases**, versus **82** for docstring-only; overlap **59**, so the reported **40 additional / 10.53%** is newly addressed cases, **not net improvement** (net +17/380 = 4.47 points). Manually assessed; early Copilot generation rather than modern agentic edits. The mechanism is ambiguous instructions: descriptions of missing functionality can cue reproducing the omission. Avoid simplifying this into “TODOs worsen code by 35%.”

4. **[Testing the Effect of Code Documentation on LLM Code Understanding](https://aclanthology.org/2024.findings-naacl.66.pdf)**, NAACL Findings 2024. Confirmed your source: 164 HumanEval reference implementations; GPT-3.5-turbo and GPT-4 generating tests. Wrong-topic docstrings lowered test success from **44.7% to 22.1%** and **78.5% to 68.1%**, respectively. Correct documentation did **not significantly improve test success**, but **did significantly improve line coverage**. This distinction matters: “comments made no difference” would misstate the result. Incorrect conditions replace documentation with another function’s docstring, so they are stronger disruptions than ordinary slight staleness.

5. **[Talking to Itself While Coding](https://arxiv.org/html/2609.09242v1)**, September 2026 preprint. Your interpretation is correct: **+17.2 percentage points** average on matched source-pass subsets. Strongest controlled example: **Qwen3-8B 53.6% baseline → 70.8% with correct comment → 48.2% with a minimally corrupted comment**. The correct-to-corrupted drop is significant for all four recipients. However, recipients are small models, and these are externally supplied solution hints—not ordinary maintained repository comments. Repository-level replication is weaker: of 24 corrected tests, only one reaches significance in Table 3. Avoid presenting that replication as broad statistical confirmation.

No files were written.

