# The comment hygiene skill: purpose and limits

This page explains what the `code-comments` plugin is for, where it helps, and what
it does not do. The plugin lives in
[plugins/code-comments/](../../plugins/code-comments/README.md), which also covers
install and removal. Issue
[#45](https://github.com/AndrewGodlewsky/code-comments/issues/45) tracks it.

## Why it exists

The project's original question was whether well-kept comments help a later, possibly
weaker, model make correct changes. The
[long-horizon pilot](../evaluation/pilot-report-2026-11-08.md) found no measurable
benefit. On six real pull requests, the full skill did no better than a one-sentence
instruction to keep comments accurate.

That result does not make comments useless. It means **the skill cannot be sold as a
performance improvement.** It can still do a narrower job: stop agents leaving
comments that are false, and stop them burying the code in comments that say
nothing. A false comment is a cost even when no benchmark notices it: whoever reads
it next, person or model, is told something untrue. This plugin is that narrower
job, packaged so it can be installed and switched off.

## What it does

When Claude edits, fixes, refactors or reviews code, the skill gives it a short
checklist:

1. **Keep comments true.** Fix or delete every comment the change made false. That
   includes comments outside the edited lines, such as docstrings, module headers
   and comments in calling code. Correct the text; do not mark it "outdated".
2. **Capture what the code cannot say.** When the request, a ticket, a test or a doc
   gives a reason, constraint or contract that the code does not show, write it down
   beside the code it governs.
3. **Never invent.** Write a reason only when the evidence supports it. If the reason
   is unknown, say so to the user instead of guessing in a comment.
4. **Restraint.** Don't restate code. A routine change usually needs no new comment.
   Leave accurate comments word for word.
5. **Fit in.** Match the style already in the file.

`/code-comments:stale-refs` adds a mechanical check. It lists comments in your
changes that name a function, class, flag or file that no longer exists, and Claude
then fixes each one or explains why it left it.

## What it is good at

These are the behaviours the skill and its eval are built to test. Results from the
[hygiene eval](../../evaluation/hygiene/README.md) back them up or knock them down.

- **Comments far from the edit.** An agent changes a value and fixes the comment
  beside it, but misses the docstring in another file that still states the old
  value. The skill tells it to look.
- **Renames and removals.** After a rename, comments elsewhere still name the old
  function. The lint finds these mechanically.
- **Recording a reason that would otherwise be lost.** A ticket explains that rows
  must be sorted because a downstream loader merge-joins on them. Without a comment,
  the next editor sees an unexplained sort and may remove it.
- **Not inventing reasons.** When a value changes and nobody says why, the skill
  says to report the gap, not make up a rationale.
- **Leaving good comments alone.** In a comment-only review, accurate comments,
  licence headers and tool directives stay exactly as they were.
- **Staying quiet on routine work.** Adding a simple flag should not add a paragraph
  of comments.

## What it helps with

- **Code review.** Fewer review notes of the kind "this comment is now wrong".
- **Handover.** The next person or agent can trust the comments beside the code.
- **Agent-heavy repositories.** Agents write a lot of code quickly. A small rule set
  that applies on every edit keeps comment quality from drifting.
- **Cleaning up.** A comment-only request ("check the comments in this file") fixes
  false claims without touching code.

## What it is not

- **Not a proven productivity gain.** The pilot found no downstream benefit over a
  one-sentence instruction. Treat it as hygiene, like a linter, not as something that
  makes a model smarter or a weaker model reliable.
- **Not a guarantee against stale comments.** The lint only catches names that no
  longer exist. A comment that says "retries three times" when the code now retries
  five times names nothing missing, so only reading catches it. The skill asks Claude
  to read; it cannot force it.
- **Not a documentation system.** It does not replace a README, design docs, ADRs or
  an onboarding guide. Those hold knowledge that spans files; comments hold knowledge
  about the code beside them.
- **Not a memory or index.** It keeps no central record of decisions and builds no
  map of the code. [ADR 0001](../adr/0001-context-lives-inline-no-central-index.md) explains why the
  project keeps context inline rather than in an index.
- **Not a replacement for tests or commit messages.** A test enforces a constraint;
  a comment explains it. A commit message records why a change happened; a comment
  records what the next editor needs to know. The skill does not move either into
  comments.
- **Not a style enforcer.** It does not reformat docstrings, impose a template or add
  doc comments to every function.
- **Not a fixer of old code.** It acts on code Claude is changing, plus comment-only
  requests. It does not sweep a repository for every weak comment.
- **Not a source of facts.** It cannot know a reason nobody wrote down. When the
  evidence is missing, the right output is a question to the user.

## How it is checked and improved

- **Source of truth.** The skill text is the lean variant,
  `skill-variants/lean/code-comments/SKILL.md`. The plugin carries a copy, and
  `tests/test_plugin.py` fails if they drift.
- **Version tested by the pilot.** The pilot used lean as of commit `baca8a2`. Later
  edits come from the hygiene eval below and have not been through the pilot.
- **Hygiene eval.** [evaluation/hygiene/](../../evaluation/hygiene/README.md) holds
  small, realistic editing tasks, each aimed at one behaviour above. Each case runs
  with and without the skill, and a script grades the results. That is the score
  being climbed.
- **Guarding against a bad climb.** Round 1 showed that a skill can win on a proxy
  while doing harm: weaker models given the skill rewrote valid comments. The eval
  therefore scores preservation and restraint alongside capture. A change that
  raises one at the cost of another is not an improvement.
