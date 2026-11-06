## Purpose and acceptance criteria (revision 2)

The owner has now explicitly requested committing everything on the current branch and merging it through a PR into main. This expands revision 1 from publishing the requested transcript to integrating that transcript plus the research collection created in this chat. The owner explicitly authorizes publishing these downloaded papers and the existing transcript; this overrides the normal exclusion of downloaded user content for these named files only.

1. Preserve books/The Pragmatic Programmer.txt byte-for-byte from published commit 31e7aa3c9efc7e2d7a2439f0155533316d4c27cb.
2. Commit the complete docs/research/ai-code-comments collection: four original PDFs, five separate-subagent HTML reviews (four full-text reviews and one clearly labeled abstract-only brief for the inaccessible paper), an offline HTML index, stylesheet, README source/checksum index, and unavailable-paper record. Do not represent the fifth PDF as downloaded or its full text as reviewed.
3. Verify all local HTML/Markdown links, PDF page targets and the four recorded PDF checksums; inspect offline Brave rendering at desktop and mobile widths. Summaries cover research design, models/timing, findings, limitations and practical lessons, distinguishing author findings from inference.
4. Run pwsh -NoProfile -File ./scripts/check.ps1 -Base 61b0cf5c9071c2ae9c43a47d898b81a6f14ce995 with documented dependencies. Obtain independent review of the exact published candidate/target tuple and revision 2 before merging.
5. Create and merge a PR into main with passing available CI, verify remote integration and the combined tree, preserve unrelated open acceptance work, clean up only this integrated task branch, obtain independent post-cleanup audit, then close this tracker.

## Assignment

- Branch: codex/14-book-transcript. Remote target: origin/main. Dispatch base: 61b0cf5c9071c2ae9c43a47d898b81a6f14ce995.
- Coordinator and sole Git-mutation owner: /root in the research-collection chat.
- Workspace: primary checkout A:/Claude/Book-connect; one worktree. Earlier writer finished at published transcript checkpoint 31e7aa3c9efc7e2d7a2439f0155533316d4c27cb.
- Owned paths: books/The Pragmatic Programmer.txt (preserve), docs/research/ai-code-comments/ (publish). No product code or other books.
- Reviews were authored by /root/review_self_comments, /root/review_bugfix_comments, /root/review_comment_traps, /root/review_documentation and /root/review_stale_comments. They have finished; /root owns shared index/CSS/README.
- Associated issues: #14 owns this artifact publication. #7 real-book owner accuracy acceptance and #2 release milestone remain open; this PR does not satisfy their remaining criteria.

## Progress

Revision 2 recorded November 6, 2026. Current branch has the previously published transcript and thirteen untracked research files. Remote main verified at the dispatch base. Preparing candidate checks, checkpoint and PR; independent review, integration, cleanup and final audit remain.

## Project context

The collection README records sources, availability, checksums and review entry points. Existing product intent, architecture and transcription guidance remain applicable: there is no product behavior change, no new commenting policy and no new claim of transcript accuracy.
