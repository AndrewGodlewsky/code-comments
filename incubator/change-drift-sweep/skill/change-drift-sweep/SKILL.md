---
name: change-drift-sweep
description: Sweep the repository for prose that still states an old value after your change gives a constant, default, limit, timeout, interval, count, size or unit a new value, or renames or moves a flag, config key, function or file. It finds the old value in the comments, docstrings and Markdown docs of every file, written in digits, number words, other units (7200 seconds written as two hours) or figures derived from it (a total wait, a product, a per-day count). It corrects living descriptions of the code, keeps records (released changelog entries, ADRs, dated reports, migration notes) and outside facts word for word, and reports the rest. Use it before finishing any such edit, even when the request never mentions comments or docs, and when asked which docs a change affects. Not for reviewing a finished diff someone else wrote, writing new docs, retiring a docs page, or comment wording in general, which the code-comments skill covers.
---

# Change drift sweep

A change that gives something a new value, name or place leaves **drift**: prose
elsewhere that still states the old one. Nothing fails and no name goes missing, so
only reading catches it. After any edit that re-values a constant, default, limit,
timeout, interval, count, size or unit, or renames or moves a flag, config key,
option, function or file, **sweep** before your final reply: list every form the old
value takes, search all the prose for each, and sort every hit.

This complements the `code-comments` skill, whose rules govern how each correction
reads. Its "fix every comment your change made false" says what to fix; this skill
finds restatements of the old value anywhere and says which to keep. Its
`/code-comments:stale-refs` lint finds comments naming code that no longer exists; it
compares no values and does not check Markdown prose.

## 1. List the old forms
Before searching, write down every way prose could state what you changed:
- digits, with and without thousands separators (7200, 7,200);
- number words (nine, twenty-five). Style guides spell out small numbers, so small
  counts are often words;
- every other unit, and hyphenated adjectives (7200 s, 120 min, 2 h, a two-hour wait);
- every **derived figure**: a total, a product, the terms and sum of a wait sequence,
  a per-hour or per-day count. Work each out from the old code. A derived figure often
  does not contain the old value at all;
- for a rename or move: the old name, flag, key or path, including in backticks,
  fenced examples and relative link targets.

## 2. Search all the prose
Search the comments and docstrings of every code and config file, and every Markdown
and text doc, not only the files you edited.

**With the script**, `scripts/value_drift.py` in this skill's folder (the folder that
holds this file), on Python 3.10 or newer:

    python <skill folder>/scripts/value_drift.py <repository root> --old "7200 s" --new "10800 s" --old 12

- Repeat `--old` for the old value and each derived figure. A number can carry its
  unit (ms, s, min, h, day, week, B, KB, KiB, MB, MiB, GB, GiB), or `--unit` sets one
  for all. A name, flag or path matches as text; for one that starts with a dash,
  write `--old=--legacy`.
- A value under 10 matches many unrelated lines. Search it in a call of its own, with
  `--near` and words for the thing you changed, such as `--near "replica|shard"`, to
  keep only hits on or beside a line that names it. `--near` and `--unit` apply to
  every `--old` in the call, so in a shared call they also drop or misread the other
  forms, such as a derived figure on a line that never names the thing.
- Add `--strings` to read string literals in code too: help text, error and log
  messages.
- Each hit is `file:line`, where it sits (comment, docstring, string, doc, or fenced in
  a doc), the form matched, and hints: `record?` or `instructions?` from the path, and
  `states new` when the line already has the `--new` value. It exits 0 whether or not
  it finds hits.
- It reads the files fresh, writes nothing and stores nothing. It cannot compute
  derived figures or see paraphrase: pass what you worked out, and read each hit.
- It skips `build/` and `dist/` folders and files over 2 MB, and prints them as "not
  read". Search any of those that could state the value, for example by passing the
  folder as the root.

**Without the script**, grep (or `rg`) the whole repository, ignoring case, one `-e`
per form, and keep the hits in comments, docstrings, docs and user-facing strings
(help text, error and log messages):

    grep -rnIiE --exclude-dir=.git --exclude-dir=node_modules -e '(^|[^0-9.,])7,?200($|[^0-9])' -e '\b(2|two)[ -]?(h|hrs?|hours?)\b' -e '\b120[ -]?(m|mins?|minutes?)\b' <repository root>

## 3. Read and sort every hit
Change a hit only when its sentence is about the thing you changed. Sort each hit:
- **Living description** of this code: a comment, docstring, README, current docs
  page, usage example, link target, or a user-facing string such as help text or an
  error message. Correct only the false clause and keep the rest word for word.
- **Record**, true about its own date or version: a released changelog entry, an ADR
  or decision record, a dated report, an incident or migration note. Keep it word for
  word. A page that says how the code works now is living wherever it sits; `record?`
  is only a guess from the path (judgement).
- **Outside fact**: a vendor quota, a law, another team's limit. Keep it as written;
  if your change now breaks it, say so in the reply.
- **Instruction file** (AGENTS.md, CLAUDE.md, editor rules): leave it unless the user
  asked for it, and give the line and its replacement in the reply.
- **Unrelated**: a fact that shares the number but describes something else. Leave it.

If the change contradicts an ADR, keep the ADR and say it may need superseding. Add a
changelog line only under an existing `Unreleased` heading.

## 4. Correct
- Recompute every derived figure from the new code. Show the arithmetic, or run a
  one-line snippet such as `python -c "print(86400 // 10800)"`.
- Keep the sentence's own form: a word stays a word, minutes stay minutes (judgement).
  Where the copy only restates a constant, naming the constant instead is also a
  correction (`code-comments`: point to a fact rather than copy it).
- A comment that names the constant without stating its value is already true; leave
  it word for word. State the current value only; history belongs in the commit.
- A sentence already false before your change is not your drift. Always report it,
  with both values. Either leave it, or correct it toward the code, which is what runs,
  changing only the false figure. Never change the code to match it unasked (judgement).
- For a rename or move, also run `/code-comments:stale-refs` when it is installed. It
  skips Markdown, so check that every relative link you changed still resolves.

Done when every form on your list has been searched, every hit is sorted, and no
living description still states the old value.

## Reply
- What you corrected, by file.
- The records, outside facts and instruction-file lines you kept, and why.
- Drift your change did not cause, with both values and whether you corrected it, and
  any conflict with an outside fact or an ADR.

No rule here has been shown to improve results; each is a hypothesis until an eval
tests it. Rules marked *judgement* have no source.
