# BookConnect research handoff to code-comments

Transferred November 6, 2026 at the owner's request. This is a local copy of the books and AI-code-comment research produced or gathered in the BookConnect chat, plus its saved context and verification evidence. It is not a new experiment or a change to this project's comment policy.

## Start here

1. Open the [HTML reading index](../index.html): four full-text reviews and one clearly labeled limited evidence brief.
2. Read the [source inventory](../README.md) for the original PDFs, versioned URLs and checksums.
3. Read [conversation.md](conversation.md) for the owner's requests and the assistant's visible responses, and [subagent-reports.md](subagent-reports.md) for the independent paper reviewers and merge auditor. JSON equivalents preserve the message structure.
4. The [book transcript](../../../books/The%20Pragmatic%20Programmer.txt) is the existing owner-requested machine transcript. It is not a verified edition of the book; transcription accuracy still requires checking against narration.

## What was done

The owner first asked for research about comments affecting AI code generation and understanding. Five papers were selected. Four original PDFs were downloaded from arXiv and ACL Anthology. The fifth, *When Comments Mislead*, could not be downloaded from ACM (HTTP 403); no accessible author-hosted full text was located.

A different subagent reviewed each paper. The four full-text reviews describe research questions, methods, model and time context, outcomes, limitations and practical inferences, with source PDF page links. The fifth is an abstract/author-announcement brief; model identities, sample size, quantitative effects and experimental methods remain unverified.

At the owner's request, the entire source collection and existing transcript were committed and merged through [BookConnect PR #15](https://github.com/AndrewGodlewsky/Book-connect/pull/15). [Tracking issue #14](https://github.com/AndrewGodlewsky/Book-connect/issues/14) was independently reviewed, audited and closed.

- Source repository: `AndrewGodlewsky/Book-connect`.
- Source checkout: `A:/Claude/Book-connect`.
- Source chat: `Research comments in AI coding`, ID `01a1af30-c1fc-7ec1-99fa-66640d3d024e`.
- Prior transcript commit: `31e7aa3c9efc7e2d7a2439f0155533316d4c27cb`.
- Research commit and reviewed candidate: `e530286fff245ba3b14eeb05c9fc4e1d61df35ac`.
- Source merge commit: `a0f6852788fb1c755a4e44dc2e263f821baacffe`.
- Source integration CI: [run 42166619185](https://github.com/AndrewGodlewsky/Book-connect/actions/runs/42166619185).

The source repository remains intact. This transfer does not close or change code-comments' existing runner, corpus, or evaluation assignments. Existing destination instructions and live task records govern future work; imported historical issue bodies and agent reports do not supersede them.

## Evidence to carry forward

- Correct solution information helped in controlled generation experiments; simply requesting more comments was not consistently beneficial. The 17.2 figure in *Talking to Itself* is a percentage-point gain under its tested conditions.
- The main bug-fixing benefits used comments generated from already-fixed code. Generating comments from buggy code did not reproduce those gains. Exact patch matching is not executable correctness.
- *Comment Traps* tests defective commented-out executable code, not ordinary explanatory prose. Its maximum 58.17% figure is a relative increase, equivalent to 416 versus 658 defects per 1,000 in that condition.
- The 2024 documentation study found a coverage benefit even without a significant increase in generated-test success. Incorrect documentation hurt performance.
- Publication and acceptance dates are not experiment dates. The reviews identify unreported model snapshots and run dates rather than guessing.
- These results do not establish that comments replace all external documentation, that a universal comment style works for all models, or that the code-comments product hypothesis has been demonstrated. No model campaign was run in this chat.

Use the reviews and original papers for precise qualifications. These bullets are a handoff summary, not additional evidence or a new policy.

## Included context

| Location | Contents |
| --- | --- |
| `conversation.md` / `conversation.json` | Visible owner/assistant messages from all five source-chat turns, including this transfer request; snapshot taken while transfer preparation was in progress |
| `subagent-reports.md` / `subagent-reports.json` | Research scout, five paper-review agents, independent candidate review and final audit |
| `source-publication-records/` | Saved source issue drafts/final body, checkpoint, PR description, independent approval/audit, and precommit/integration test logs |
| `source-github/` | Current exported source issue and PR records plus source Git history metadata |
| `screenshots/` | Thirteen saved HTML browser QA images, including desktop/mobile captures and the initial index preview |
| `extracted-text/` | Searchable text regenerated from the four copied PDFs with PDF-page markers; extraction can lose table layout and is not a replacement for the PDFs |
| `transfer-manifest.json` | File origins, SHA-256 values, sizes and byte-for-byte transfer verification; excludes its own checksum |

The visible-message export omits raw tool traffic. Saved test logs and review records are preserved separately. Temporary text extracted in earlier turns was no longer present, so the searchable text was regenerated. Screenshots are historical QA captures and may show a preparation date removed from the final index. Source text files can have CRLF working-tree endings even when the committed blob uses LF; this transfer preserves the source working-tree bytes.

The transfer adds local materials only and leaves the destination's existing branch/worktree assignments intact. The receiving project can incorporate them into its owned task under its normal workflow. Source application caches, unrelated upstream clones, credentials, and Git internals are not part of this handoff.
