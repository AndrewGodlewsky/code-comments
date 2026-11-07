# Inline-only context: pros, cons and open questions

For the user's review (2026-11-07). The decision itself is recorded in
[ADR 0001](../adr/0001-context-lives-inline-no-central-index.md): context lives in
comments as close as possible to the code it describes, with no central index or
docs view. This document tests that decision. It sets out where the approach is
strong, where it is weak, and what would mitigate each weakness **without breaking
the decision**, meaning nothing that a human editing code by hand can leave out of
sync.

Evidence tags: **[measured]** = an experiment or mining study; **[report]** =
practitioner or vendor report; **[reasoning]** = argument, not yet tested. Sources
are in the linked research reports. The empirical questions are what #19 is
designed to answer.

## The idea in one paragraph

The code is the source of truth, because it is what runs. Any explanation kept
elsewhere is a second source that can disagree with it. So put the knowledge an
editor needs (why the code is this way, what it must not break, what it affects) in
comments at the exact place it matters. An agent or a person editing that code sees
it because they have to open the file. Anything stored elsewhere is plain text
beside the code it describes, and `grep` or `ripgrep` can find it.

## Pros

| # | Strength | Evidence |
| --- | --- | --- |
| P1 | **One artefact to maintain.** A change touches the code and the comments beside it, in the same file, the same diff and the same review. There is no second place to remember | [measured] Comments change together with code far more often than separate docs (90-97% of comment changes happen with a code change; R3). Separate docs drift for years: 82% of top projects had stale references at some point (R3) |
| P2 | **Seen at the point of edit, without a lookup step.** Neither an agent nor a person has to know that context exists, or where | [measured] Developers start from code and inline comments, and docs were consulted in 12 of 357 observed events (R3). Agents read the files they edit |
| P3 | **Works for people without AI.** A developer editing by hand sees and updates the comment in front of them. Nothing needs regenerating | [reasoning] This is the user's human-editor argument, and the reason an index was rejected (ADR 0001) |
| P4 | **Reviewers can catch drift.** A stale comment beside changed lines sits in the same hunk of the diff, where a reviewer can spot it | [reasoning] Separate docs are not in the diff at all unless someone remembers them |
| P5 | **No infrastructure.** No index format, generator, service or memory, so nothing breaks when tools change | [reasoning] |
| P6 | **Targets the knowledge that matters most.** Local constraints, effects and rejected alternatives are the least-recorded and hardest-to-find knowledge today, and comments are their natural home | [measured] Rationale is mostly scattered across issues and PRs, and inline comments held 0.4% of it (R4). Context helps most when it carries knowledge the code lacks (R2) |
| P7 | **Version-controlled with the code.** The explanation always matches the revision it sits in. Checking out an old commit gives the old explanation | [reasoning] |

## Cons, with mitigations that keep the decision

| # | Weakness | Evidence | Mitigation within ADR 0001 |
| --- | --- | --- | --- |
| C1 | **Knowledge about effects elsewhere may not be seen.** If changing `A` breaks `B`, and the fact is written only in `B`, an agent editing `A` never opens `B`. This is the "this affects that" case the user cares most about | [measured] Frontier agents found the right file but fixed the symptom, not the root cause, in 10 of 12 hard tasks (R2). Discoverability mattered in one vendor test: an always-loaded index scored 100% against 79% for on-demand context (R1, vendor claim) | Write the fact at the owner, **plus a short pointer at the sites that depend on it** ("callers rely on this ordering: see `rebuild_index`"). The skill already has this as AXIS-REPEAT position b. Test it directly in #19, with steps whose knowledge lives in another file |
| C2 | **No natural home for the big picture.** "How these modules fit together" belongs to no single function | [reasoning] The user's docs folder probably helped here | Module and package docstrings (`__init__.py`, file headers) are in the code, so they satisfy the decision. A README for orientation is a separate, human-facing document (intent.md allows selective replacement) |
| C3 | **Comments drift too.** Closer is not immune; comments at callers and interfaces lag behind | [measured] Stale comments are found even in active projects, and the lag is worst at interfaces and callers (R3) | The skill's top duty is to find and fix comments the change falsifies, including at callers (P-01). A **mechanical lint** can flag comments that name identifiers that no longer exist; it reads the code, so it adds no second source |
| C4 | **A stale comment at the point of edit may mislead more than a stale doc nobody opens.** Proximity cuts both ways | [measured] Wrong comments harm models, especially weaker ones (ledger P-01, grade A; R2). Comments raised human confidence more than accuracy (R3). Whether a stale inline comment is worse than a stale doc is [reasoning] | Keep comments short and specific, so they are easy to verify. Tell readers to treat comments as claims to check against the code (P-21). Test with #19's drift steps D1 and D2 |
| C5 | **Context cost.** Comments are read every time a file is opened, including the irrelevant ones | [measured] Context that restates code added about 20% cost with no gain for strong models (R2) | Restraint duties: no restating, comment only what a reader could get wrong (P-09, P-10). The noise metric guards against bloat |
| C6 | **Clutter for human readers.** Too many comments make code harder to read | [report] A common complaint about comment-heavy code | The same restraint. The skill's `restrain` eval family exists to catch it |
| C7 | **Some knowledge has no code to sit beside.** Deployment topology, external service contracts, product decisions, onboarding | [reasoning] | Out of scope by design. These belong to instructions and intent or to decision memory (layers 1-2). The skill doesn't try to replace them |
| C8 | **Not all files take comments well.** Generated code, minified output, some config formats, binary assets | [reasoning] | Comment the generator or source, not the output. A gap, but a small one for most codebases |
| C9 | **Executable checks can beat prose.** A test or type that enforces a constraint cannot drift silently | [reasoning, consistent with ledger P-25] | Prefer a test, type or assertion where the task allows it, and comment what cannot be enforced (P-25, family-aware). Comments complement checks; they don't compete |
| C10 | **Search depends on wording.** Plain-prose comments may not be found by `grep` with the words the searcher thinks of | [reasoning] | Consistent vocabulary (P-31). A tag convention (#34, later) would make search more precise while keeping the text in the code |

## What the evidence cannot yet say

- Whether point-of-edit comments actually improve a **later agent's** edits more than a
  docs folder does, over many changes. **#19 is designed for exactly this.**
- Whether pointer comments (C1) are enough for cross-file effects, or whether agents
  still miss them.
- Whether humans editing by hand keep inline comments current in practice. R3 says
  comments do much better than separate docs, but no study covers AI-written code
  specifically.

## How #19 will test this document

| Claim | #19 condition |
| --- | --- |
| P1, P3, C3 (drift) | Drift steps D1 (nothing updated) and D2 (a realistic human: the comment at the edit is updated, callers and docs are not), compared across arms |
| P2, C1 (point of edit vs effects elsewhere) | Reader steps tagged **local-visible** vs **non-derivable / cross-file**, with predictions written down before the run |
| C4 (stale inline misleads) | Record whether the reader followed a stale claim, noticed the conflict, or checked the code |
| C5 (cost) | Writer plus reader tokens and cost per successful step |

## Questions for the user

1. Is a module or package docstring an acceptable home for the big picture (C2)? It
   is in the code, but further from any one line.
2. Should pointer comments at dependent sites (C1) be a default part of the skill,
   even though they add a little text and can themselves drift?
3. Would a CI lint for comments that reference missing identifiers (C3) be welcome
   as an optional companion to the skill? It reads code only.
