# Research comments in AI coding — conversation export

Snapshot of visible user and assistant messages through preparation of the transfer on November 6, 2026. Tool traffic is omitted; saved verification logs and audit records are included separately. Historical paths refer to the source project. The current transfer is still in progress at snapshot time.

## Turn 1

### user

Can you look around to see if anyone has done research on the effects of comments when AI is trying to read and write code? I'm particularly looking to try and understand how comments will affect AI trying to write code.

### assistant (commentary)

I’ll look for research on how comments affect AI code generation and editing, including whether helpful, stale, or misleading comments change the results. I’m using the research skill to keep the findings tied to primary sources.

### assistant (commentary)

I found several studies directly on this question. A useful distinction is emerging: comments that provide correct solution details can improve generated code, but simply asking for more comments does not reliably help. Stale comments can also steer the model toward old behavior.

### assistant (commentary)

One important caveat: a bug-fixing paper’s large gains came from comments generated from the already-corrected code. When the researchers generated comments from the buggy code instead, the benefit disappeared. That makes “add accurate knowledge about intended behavior” much better supported than “have AI annotate everything.”

### assistant (final_answer)

Yes—there is research directly on this. **The strongest pattern is that accurate, relevant comments can help AI write code, while misleading comments can actively steer it toward mistakes. Simply increasing the amount of commenting does not reliably improve results.** That distinction appears across code-generation, completion, and bug-fixing experiments. [Generation study](https://arxiv.org/html/2609.09242v1), [bug-fixing study](https://arxiv.org/html/2601.23059v1).

These are the most useful papers I found:

1. **“Talking to Itself While Coding: What Makes Comments Help Code Generation?” — September 2026 preprint.**  
   This addresses your question most directly. Supplying smaller models with comments describing correct solutions improved first-attempt success by **17.2 percentage points on average**. In one controlled example, success went from **53.6% without the comment, to 70.8% with a correct comment, to 48.2% with a slightly corrupted comment**. Asking models to produce more comments themselves did not reliably reproduce the benefit; prohibiting comments helped some models and hurt others. These were solution hints in controlled tasks, so the numbers aren’t estimates for ordinary repository maintenance. [Read the paper](https://arxiv.org/html/2609.09242v1).

2. **“On the Impact of Code Comments for Automated Bug-Fixing” — January 2026 preprint.**  
   Comments substantially improved two small, fine-tuned models’ ability to reproduce fixes. But there is a crucial caveat: the helpful comments were generated from the **already-fixed code**, giving the models information about intended behavior. When comments were generated from the buggy code instead, performance stayed similar or got slightly worse. This supports documenting correct requirements—not automatically annotating existing code and assuming that improves it. [Read the paper](https://arxiv.org/html/2601.23059v1).

3. **“When Comments Mislead” — ASE 2026.**  
   This study reports that stale comments can bias completions **toward historical implementations**. The resulting code can look plausible while being wrong precisely where behavior has changed. I could verify the official conference abstract, but not inspect the full experimental methods, so I would treat this as corroborating evidence without attaching a numerical effect size. [Conference abstract](https://conf.researchr.org/details/ase-2026/ase-2026-research-track/29/When-Comments-Mislead-An-Empirical-Study-of-Outdated-Comments-in-LLM-Based-Code-Comp).

4. **“Comment Traps” — accepted at FSE 2026.**  
   Researchers tested Copilot and Cursor with GPT-4o and Claude 3.5 Sonnet. Leaving defective code in **commented-out blocks** increased defects in generated completions. In the largest reported case, defective outputs rose from **416 to 658 out of 1,000**. This concerns disabled code, rather than explanatory prose, but shows that “the compiler ignores this” does not mean the AI ignores it. [Read the paper](https://arxiv.org/html/2512.20334v1).

5. **“Testing the Effect of Code Documentation on Large Language Model Code Understanding” — NAACL Findings 2024.**  
   GPT-3.5 and GPT-4 generated tests for existing functions. Correct documentation did not significantly improve test success, although it **did improve code coverage**. Incorrect documentation significantly hurt results. This is evidence about reading code and writing tests, rather than implementing features. [Read the paper](https://aclanthology.org/2024.findings-naacl.66/).

**My practical interpretation:** write comments that supply information the AI would otherwise have to guess:

- Intended behavior, constraints, edge cases, and reasons for surprising choices.
- Specific algorithm details when those details matter.
- Clear descriptions of what must remain true during an edit.

For example, a useful comment might be:

```python
# Preserve input order: callers match each result to its original request.
```

I would prioritize correcting stale comments and removing obsolete commented-out implementations over adding more commentary everywhere. I also wouldn’t adopt a blanket “never write comments” rule: the evidence does not support that universally.

The main limitation is that these studies cover particular models and controlled tasks. They establish that comments can materially change generated code; they don’t establish one optimal commenting style for every modern coding agent.

## Turn 2

### user

Are you able to download all of those papers from all of this research that you're listing and save it into this repository in a new folder?

### assistant (commentary)

I’ll download the five papers into a new research folder, with a source index noting any paper whose full text isn’t available. I’ll first check the repository’s task routing and existing research layout.

### assistant (commentary)

Four PDFs are downloaded. ACM denied access to “When Comments Mislead,” so I’m checking for an author-hosted copy before recording it as unavailable.

### assistant (final_answer)

Saved **4 of the 5 papers** in [docs/research/ai-code-comments](A:/Claude/Book-connect/docs/research/ai-code-comments), with a [README index](A:/Claude/Book-connect/docs/research/ai-code-comments/README.md) containing source links and reading notes.

“When Comments Mislead” couldn’t be downloaded: ACM returned an access-denied response, and I couldn’t find an accessible author copy. Its reference is preserved in the folder.

All four PDFs validated successfully. Files are saved locally, not committed or pushed.

## Turn 3

### user

For each one of these papers, can you send out a subagent to review the paper and create for me a high-level understanding of:&#x20;

- the research that the paper did
- the context as to what models and when the research was done
- the general results and findings from the paper
- anything else that would be important for knowledge transfer from the paper that I can learn

&#x20;please include these summaries as HTML files inside the folder you created.

### assistant (commentary)

I’ll assign a separate subagent to each paper and save an HTML summary beside the PDFs. Each summary will cover the study design, models and timing, findings, limitations, and practical lessons. For the paper without accessible full text, I’ll clearly distinguish what the abstract supports from what remains unknown.

### assistant (commentary)

I’m using the structured-artifact skill for a consistent reading layout: the main takeaway first, followed by evidence, caveats, and source references. I’ll keep publication dates separate from experiment dates where the papers report both.

### assistant (commentary)

The reviewers are finding caveats worth including. The bug-fixing paper uses exact matches to reference patches, while the commented-out-code paper counts defects detected by static analysis. The summaries will explain those measures—and distinguish publication dates from experiment dates, which several papers don’t report.

### assistant (commentary)

Three full-text reviews are written, and the remaining two are underway. Each review links to the relevant PDF pages and labels practical advice as interpretation. The finished pages also pass offline checks in Brave at desktop and phone widths.

### assistant (commentary)

All five HTML files are ready, including the clearly labeled abstract-only brief. Offline rendering, navigation, PDF page links, and source-file checksums passed. The repository test run hit errors in the restricted environment; I’m rerunning it with the access used for the earlier successful check.

### assistant (final_answer)

Created **five HTML summaries**, each reviewed by a separate subagent.

[Open the research reading index](A:/Claude/Book-connect/docs/research/ai-code-comments/index.html)

Each covers the research design, models and timing, findings, limitations, practical lessons, and source references.

“When Comments Mislead” is clearly labeled an **abstract-only brief**, since its full text remains unavailable.

Verified offline rendering in Brave at desktop and phone widths, local links, and PDF references. Repository checks passed: 75 tests passed, 15 skipped.

Files are saved locally in the existing folder, not committed or pushed.

## Turn 4

### user

Can you please make sure you commit everything to the branch, and then can you merge it all as a PR into main?

### assistant (commentary)

I’ll check the current branch and its tracking issue, commit the research collection, then open a PR into `main`. Before merging, I’ll run the required checks and get an independent review of the complete branch.

### assistant (commentary)

The branch contains the previously committed transcript plus the research files from this chat. I’ll include both in the PR, as requested, and update the tracking issue to reflect that scope. I’m using the PR skill to prepare the description and verification evidence.

### assistant (commentary)

All 90 tests pass with the installed dependencies. Staging exposed a Git configuration issue: it was treating the PDFs as text. I’m adding a folder-specific binary rule and verifying that the committed PDF bytes match the downloads.

### assistant (commentary)

The collection is committed, and [PR #15](https://github.com/AndrewGodlewsky/Book-connect/pull/15) is open. Local checks passed all 90 tests. GitHub CI and the independent review are running; once both pass, I’ll merge and verify `main`.

### assistant (commentary)

All GitHub CI checks have passed. The independent reviewer has also confirmed that the transcript is unchanged, all four PDF checksums match, and all 90 tests pass. They’re finishing the HTML checks before issuing the merge verdict.

### assistant (commentary)

[PR #15](https://github.com/AndrewGodlewsky/Book-connect/pull/15) is merged into `main`. I’m now verifying the merged commit, updating the local checkout, and completing the required branch cleanup and final audit.

### assistant (final_answer)

Everything is committed and merged into `main` through [PR #15](https://github.com/AndrewGodlewsky/Book-connect/pull/15).

- All 90 tests and GitHub CI passed.
- Independent review and final audit passed.
- Local checkout is clean on `main`.
- Merged branch cleaned up; tracking issue closed.

Merge commit: `a0f6852`.

## Turn 5

### user

Can you take everything that we've created in the books folder? And in the research AI code comments folder, basically everything that we created in this chat (not only the documents but also all the context or anything else that was saved), can you put it in this file location? A:\Claude\code-comments because that other project needs everything we just did

### assistant (commentary)

I’ll gather the books, research papers, HTML reviews, and saved review and PR records into `A:\Claude\code-comments`. I’ll copy them so the committed originals stay intact, and add a handoff note explaining the work and where to start.

### assistant (commentary)

The destination has unfinished work on separate branches. I’ll preserve that work and add the transfer at `books/` and `docs/research/ai-code-comments/`. I’m also gathering the saved audit records, screenshots, and chat messages so the other project gets the context behind the summaries.

