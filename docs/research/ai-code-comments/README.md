# Code comments and AI coding: paper collection

Collected November 5, 2026, following the discussion of how comments affect AI code generation, completion, understanding, and bug fixing. Four of the five cited papers are saved as original PDFs; the fifth remains unavailable. These are local research downloads, not a change to BookConnect's commenting policy.

## HTML reviews

Open the [reading index](index.html) for a separate subagent's review of each paper. Each full-text review explains the study design, model and date context, findings, limitations, and practical lessons, with links to source PDF pages. The unavailable paper has a clearly labeled limited evidence brief instead of a full-text review.

- [Talking to Itself While Coding](2026-talking-to-itself-while-coding-summary.html)
- [Comments for Automated Bug-Fixing](2026-impact-of-code-comments-on-bug-fixing-summary.html)
- [Comment Traps](2025-comment-traps-summary.html)
- [Documentation and Code Understanding](2024-code-documentation-and-llm-understanding-summary.html)
- [When Comments Mislead: limited evidence brief](2026-when-comments-mislead-summary.html)

The HTML files open directly in a browser and work offline with [summary.css](summary.css) beside them. Publication dates and reported experiment dates are distinguished. Practical interpretations are labeled separately from the authors' findings. These summaries do not reproduce the experiments or establish a new repository commenting rule.

## Original papers

| Paper | Local copy | Source and version | Pages |
| --- | --- | --- | --- |
| Talking to Itself While Coding: What Makes Comments Help Code Generation? | [PDF](2026-talking-to-itself-while-coding.pdf) | [arXiv 2609.09242v1](https://arxiv.org/abs/2609.09242v1), September 2026 preprint | 25 |
| On the Impact of Code Comments for Automated Bug-Fixing: An Empirical Study | [PDF](2026-impact-of-code-comments-on-bug-fixing.pdf) | [arXiv 2601.23059v1](https://arxiv.org/abs/2601.23059v1), January 2026 preprint | 13 |
| When Comments Mislead: An Empirical Study of Outdated Comments in LLM-Based Code Completion | [Availability and source links](when-comments-mislead-unavailable.md) | [DOI 10.1145/3832783.3834359](https://doi.org/10.1145/3832783.3834359), ASE 2026 | Not downloaded |
| Comment Traps: How Defective Commented-out Code Augment Defects in AI-Assisted Code Generation | [PDF](2025-comment-traps.pdf) | [arXiv 2512.20334v1](https://arxiv.org/abs/2512.20334v1), December 2025 preprint; reports acceptance at FSE 2026 | 21 |
| Testing the Effect of Code Documentation on Large Language Model Code Understanding | [PDF](2024-code-documentation-and-llm-understanding.pdf) | [ACL Anthology](https://aclanthology.org/2024.findings-naacl.66/), NAACL Findings 2024 | 7 |

## Reading notes

- **Talking to Itself:** distinguishes accurate externally supplied solution hints from simply prompting a model to generate more comments. Its numerical gains are not estimates for routine repository maintenance.
- **Automated Bug-Fixing:** the main helpful comments were generated from already-fixed code. Comments generated from buggy code did not deliver the same benefit. The models were small and fine-tuned; exact-match results are not general agent success rates.
- **When Comments Mislead:** only the conference abstract was available in this research session; its full methods and effect sizes have not been checked.
- **Comment Traps:** studies defective commented-out executable code, not ordinary explanatory prose. Its maximum 58.17% increase is relative, not a defective-output percentage.
- **Code Understanding:** evaluates test generation with GPT-3.5 and GPT-4. Correct comments improved coverage without significantly improving test success; mismatched documentation hurt results.

## Download verification

The four downloads have PDF signatures and parse successfully with Poppler `pdfinfo`. Page counts are recorded above. SHA-256 checksums identify the exact downloaded bytes:

```text
3668a4e26feef03efab97d92ba3b2ad0c45f2fd902fb06d9522f4a4ea0754f84  2026-talking-to-itself-while-coding.pdf
e61258622ed2e116e18593fbfe9a8c4f716d591855ec638b25755e1bb8ea1c16  2026-impact-of-code-comments-on-bug-fixing.pdf
84f85e947273a08891a12aeb606aa6d061cc61a335d84f727c00435ea0a5152d  2025-comment-traps.pdf
55908b4e14276d869c3107b5131182815381ebf35e5151f920794eea94bcde53  2024-code-documentation-and-llm-understanding.pdf
```

Original author and publisher notices remain in the unmodified files. Inclusion here does not relicense the papers under the repository's software license.
