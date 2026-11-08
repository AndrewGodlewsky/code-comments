# code-comments plugin for Claude Code

This plugin adds comment hygiene to coding sessions. While Claude edits code, it
keeps the comments true, records the reasons the code cannot show, and does not add
comments that only restate the code. It also adds `/code-comments:stale-refs`, a lint
for comments that name code which no longer exists.

The [purpose document](../../docs/skill/hygiene-skill.md) explains the purpose, what
the skill is good at, and what it is not meant to do. Read that before you rely on
it.

## Install

In Claude Code:

```
/plugin marketplace add AndrewGodlewsky/code-comments
/plugin install code-comments@code-comments
```

To try a local checkout instead, run `/plugin marketplace add <path to this repository>`.

The skill loads on its own when you ask Claude to edit, fix, refactor or review code.
You can also ask for it by name ("use the code-comments skill").

The stale-reference command needs Python 3.10 or newer on `PATH` and a git
repository. It uses nothing outside the standard library.

## Turn it off or remove it

- **Turn it off for now:** run `/plugin`, choose `code-comments`, and disable it.
  Enabling it again restores it.
- **Remove it:** run `/plugin uninstall code-comments@code-comments`. To drop the
  marketplace too, run `/plugin marketplace remove code-comments`.

The plugin adds no hooks, so nothing runs unless the skill loads or you call the
command.

## What it claims

- It gives Claude a short, specific checklist for comments during code changes:
  - fix or delete comments the change made false, including ones outside the edited
    lines;
  - record constraints and reasons that the evidence supports;
  - write nothing that the evidence does not support;
  - leave accurate comments alone.
- `/code-comments:stale-refs` lists comments in your changes that name a function,
  class, flag or file that no longer exists. Claude then fixes them or explains why
  it left them.

## What it does not claim

- **That it makes later work better.** In a six-step pilot on a real project, this
  skill did no better than a one-sentence instruction to keep comments accurate.
  See the [pilot report](../../docs/evaluation/pilot-report-2026-11-08.md).
- **That it catches every stale comment.** The lint finds names that no longer exist.
  It cannot tell whether a comment's description of behaviour is still true.
- **That it replaces documentation, tests, ADRs or commit messages.** It keeps the
  explanation beside the code accurate. It is not a memory system or an index.

## Keeping it in sync

`skills/code-comments/SKILL.md` is a copy of
`skill-variants/lean/code-comments/SKILL.md`, and `scripts/stale_refs.py` is a copy
of the repository's `scripts/stale_refs.py`. `tests/test_plugin.py` fails if either
copy drifts from its source, so edit the source and copy it across.
