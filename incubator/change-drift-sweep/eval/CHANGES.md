# change-drift-sweep: skill changes

Each version lists what changed in `skill/change-drift-sweep/` (SKILL.md and the script)
and why. The evidence behind each change is in the iteration-1 analysis (ANALYSIS.md,
"Iteration 1"). No change was informed by the held-out cases. They were not run, and
their contents were not opened. One recursive directory listing printed their file and
grader file names (README Provenance).

## v2 (after iteration 1)

One revision, with two changes: one to the script and one to SKILL.md. Both target a
miss in the search step of `with_skill` runs. Neither one changed a graded result. Every
`with_skill` run passed every check, and each run made up for the miss by reading every
file. Both changes are written about the behaviour, not about a fixture.

Checks after the change:
- `python incubator/harness.py lint change-drift-sweep` printed `lint ok`.
- `self-test ok` still holds.
- The script's unit tests pass: 36, up from 33 (`python -B -m unittest` in `scripts/`).
- The SKILL.md body grew from 102 to 104 lines, as the linter counts them.

1. **The script reads a line together with the next line of the same block.**
   - **What changed.** `scan` now matches each prose line joined to the line after it,
     and lists only the forms that start on the first line, at that line. It joins two
     lines only when all of these hold:
     - the next line is the same kind of prose (comment, docstring, string, doc or
       fenced) and has the next line number;
     - neither line is blank;
     - the next line does not open a new Markdown block (list item, quote, table row or
       heading);
     - the first line is not a heading or a table row.

     A line that ends in a hyphen joins without a space, so a hyphenated adjective split
     at its hyphen is found. A number at the end of a line is now judged by the unit that
     starts the next line: "7" followed by "days" is not 7 seconds. The module docstring
     says this.
   - **Why.** In `unit-spelled-ttl`, the script left out the same docstring sentence in
     3 of 3 Haiku `with_skill` runs. The sentence states the old timeout as an idiom that
     wraps across a line break, and the script matched one line at a time. Two of the
     runs passed that very phrase as `--old`. The third passed the old value with its
     unit, whose conversions include the idiom. Each run fixed the sentence only because
     it had already printed every file. In a repository too large to read whole, a run
     that trusted the script's list would have left the sentence false. Docstrings,
     comments and Markdown paragraphs all wrap, so the fault is not tied to one fixture.
   - **Tests.** Three new unit tests, worded apart from every case:
     - a wrapped idiom in a docstring, a hyphenated adjective split at its hyphen in a
       comment, a number word and its unit on two Markdown lines, and literal text split
       across lines;
     - the unit on the next line decides whether a bare number is the value;
     - no join across a blank line, a new list item or a heading, while a list item's
       indented continuation does join.
   - **Checked on the training fixtures.** The missed sentence is now listed. With the
     runs' own arguments, the hit counts on the other four fixtures are unchanged.
   - **Left for the coordinator.** README.md's "The script" section should say the same
     thing. README.md is outside this role's write scope.

2. **SKILL.md: a small value gets a call of its own.**
   - **What changed.** The `--near` bullet now says to search a value under 10 in a call
     of its own. It also says that `--near` and `--unit` apply to every `--old` in the
     call, so in a shared call they also drop or misread the other forms, such as a
     derived figure on a line that never names the thing.
   - **Why.** Haiku `with_skill` run 1 of `unit-spelled-ttl` ran one call with three kinds
     of value: a value under 10, the old timeout, and a derived figure. As the bullet
     said, it added `--near` because of the small value. The filter then dropped the
     derived figure's line, because that line names neither of the subject words. The
     same call's `--unit min` turned the old value, given in seconds, into minutes. The
     run fixed the line by reading. This is 1 run in 15, so the evidence is thin, but the
     rule is about the scope of two flags, and it costs one sentence.

### Considered and not changed in v2

- **Longer replies.** `with_skill` replies were the longest on both models: a mean of 228
  words on Haiku against 186 for the bare model, and 245 against 169 on Sonnet. Part of
  the extra length is sentences that report an empty category ("none found", "no
  changelog, ADR or instruction file ..."). The reminder arm writes these too. The reply
  list is the skill's designed duty, and only one check grades it. A rule to leave out
  empty items is a candidate for v3, if iteration 2 shows the length again.
- **Restating the new value rather than naming the constant.** `with_skill` runs always
  wrote the new figure into the prose. Runs of the shipped skill often pointed to the
  constant instead. Both pass, and SKILL.md already allows naming the constant. This is
  not a failure.
- **Ordered-list numbers read as values.** The script listed one runbook step number
  ("3.") as the value 3. The run left it alone, and no failure followed.
- **Sonnet never ran the script.** In all 10 `with_skill` runs it printed every file and
  edited with `sed`. The script is optional by design, so this is not a failure.

## After the runs (review fixes, 2026-11-11)

A code review after every run changed the script and one SKILL.md bullet. No run used
these changes: every iteration's `skill-snapshot/` keeps the version that was run, and
no result was regraded because of them.
- **Halves.** Number words now include a whole number and a half, so 150 s or 2.5 min
  lists "two and a half minutes". `--old "2 min"` no longer lists "two" inside it. The
  held-out runs scored the earlier script, so `poll-interval-average-wait` no longer
  tests this gap blind.
- **What it skips is named.** `build/`, `dist/` and `*.egg-info` folders and files over
  2 MB are listed as "not read" (`not_read` in `--json`), and a file that is not UTF-8
  is read with replacement characters and listed, where before all of these were
  dropped without a word. SKILL.md section 2 gained one bullet saying so.
- **Terraform.** `.tf`, `.tfvars` and `.hcl` files are read for `#`, `//` and `/* */`
  comments; before, only `#`.
- **One-letter units keep their case.** `--unit M` is an error and `--old "5 M"` is
  literal text, where before both meant 5 minutes.
- **Line numbers are counted once.** The comment scanner no longer recounts newlines
  from the top of the file for each comment, which took seconds on a 1 MB file.

The script's tests went from 36 to 41.
