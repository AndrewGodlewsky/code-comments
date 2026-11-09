# code-comments plugin for Claude Code

This plugin adds comment hygiene to coding sessions. While Claude edits code, it
keeps the comments true, records the reasons the code cannot show, and does not add
comments that only restate the code. It also adds `/code-comments:stale-refs`, a lint
for comments that name code which no longer exists.

The [purpose document](../../docs/skill/hygiene-skill.md) explains the purpose, what
the skill is good at, and what it is not meant to do, with worked examples. Read that
before you rely on it.

## What it does

When Claude edits, fixes, refactors or reviews code, the skill gives it a short
checklist:

1. **Keep comments true.** Fix or delete every comment the change made false,
   including docstrings, headers and callers outside the edited lines.
2. **Capture what the code cannot say.** Write down a reason, constraint or contract
   that the request, a ticket, a test or a doc gives and the code does not show. When
   a simplification hides a rule, state the rule and its reason beside the new code.
   When a known issue or PR records the reason, add its id after it, as in
   "(issue #212)", so a search for the issue finds the code. A TODO or workaround
   gets the issue that tracks its removal.
3. **Never invent.** If no reason was given, record only what changed and tell you
   the reason is missing. If a change breaks a stated limit, make the change, keep the
   outside fact (a vendor quota, a law), update every statement of what the code does,
   and tell you about the conflict. Never make up an issue id.
4. **Restraint.** No comments that restate the code; a routine change usually needs
   none, and no "added for #N" tag, since the commits record which issue changed the
   code. Accurate comments stay word for word.
5. **Fit in.** Match the comment style already in the file.

A comment-only request ("check the comments in this file") fixes false comments and
changes no code.

## Where to use it

Good fits:

- **Long-lived code that someone will change again.** A true comment pays off for the
  next editor, person or agent.
- **Code whose reasons live elsewhere:** vendor limits, legal rules, downstream
  consumers, past incidents that only a ticket or a test records.
- **Refactors, renames and clean-ups,** where comments go stale and hidden rules get
  lost. Run `/code-comments:stale-refs` before opening a pull request.
- **Repositories where agents do much of the editing,** so one small rule set applies
  to every edit.

Little benefit, so turn it off if it gets in the way:

- throwaway scripts, spikes and prototypes;
- codebases that keep almost no comments by policy;
- generated code, where the generator owns the comments.

## Evidence so far

On the [hygiene eval](../../evaluation/hygiene/README.md) (iteration 4, 2026-11-08:
eleven small cases, two Haiku runs each), this version passed 97.7% of checks, against
97.0% for the previous version and 91.4% with no skill. Only this version pointed from
a reason to the issue that records it (both runs, against none for the others). The
skill also did better at telling the user a reason was missing, and cost about the
same. Runs with and without it sometimes reworded an accurate docstring. These are
small samples on one weaker model, against a bare baseline rather than a one-line
reminder, and the eval does not test whether Claude loads the skill on its own.

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
