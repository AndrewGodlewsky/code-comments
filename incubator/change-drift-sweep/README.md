# change-drift-sweep

A candidate skill for the moment just after a change gives something a new value, name or
place. It finds every comment, docstring and Markdown doc that still states the old value,
in any form, corrects the ones that describe the code, and keeps the ones that are records
or outside facts.

**Status: evaluated over 165 graded runs on Claude Haiku and Sonnet. Null result: it does
not beat the one-line reminder in [eval/arms.json](eval/arms.json) or the shipped
`code-comments` skill, in training or on the held-out pair.**

Every `with_skill` run passed every check. The reminder and the shipped skill each missed
one or two checks, one run at a time, which is noise at 2 or 3 runs per cell. The skill's
only clear margin is over the bare Haiku model. The reminder closes that gap as fully, and
the shipped skill nearly so. The fixtures were small enough for every run to read every file,
so the skill's search step and its script had no room to show value. The results are in
[eval/RESULTS.md](eval/RESULTS.md), and the samples are small (see Limits).

It is ideation candidates C3 and C7
([candidates](../ideation/2026-11-11-candidates.json)) for issue
[#50](https://github.com/AndrewGodlewsky/code-comments/issues/50), as narrowed by the
coordinator's direction, and it does not ship.

- Skill: [skill/change-drift-sweep/SKILL.md](skill/change-drift-sweep/SKILL.md) (v2)
- Script: [skill/change-drift-sweep/scripts/value_drift.py](skill/change-drift-sweep/scripts/value_drift.py),
  with its tests in `test_value_drift.py` beside it
- Research: [research.md](research.md)
- Eval design: [eval/CASES.md](eval/CASES.md); case selection: [eval/GATE.md](eval/GATE.md)
- Results: [eval/RESULTS.md](eval/RESULTS.md); analysis: [eval/ANALYSIS.md](eval/ANALYSIS.md);
  skill edits: [eval/CHANGES.md](eval/CHANGES.md)

## The problem

You raise a timeout, a retry count or a page size. The constant changes, the tests pass, and
maybe the comment beside the constant gets fixed. Elsewhere the old value lives on:
- a docstring in another module that never names the constant ("keeps nine copies");
- a doc page that gives the same figure in other units ("two hours" for 7200 seconds);
- a figure worked out from the old value (a total wait, a product, a per-day count), which
  may not contain the old number at all;
- a README example that still uses a renamed flag.

Nothing fails, and nothing named has gone missing, so no lint notices. The hygiene page says
so itself: a comment that says "retries three times" when the code retries five "names
nothing missing, so only reading catches it" ([hygiene-skill.md](../../docs/skill/hygiene-skill.md)).
This is the drift [intent.md](../../intent.md) describes: "Nobody knows which documents a
change affects, so they drift."

The opposite mistake is as real. "Fix every doc the change made false", read literally,
rewrites records that are true about their own date: a released changelog entry, an ADR, a
dated report, a migration note. It can also delete an outside fact that shares the number. In
the hygiene eval a one-line reminder to "fix or delete any comment, docstring or doc that
your change makes false" deleted a true vendor quota in 3 of 5 iteration-5 runs ([research.md](research.md), R4).

## What it adds over the shipped skill and stale-refs

The shipped [`code-comments`](../../plugins/code-comments/README.md) skill already says "fix
or delete every comment your change made false", including comments outside the edited lines.
Large overlap is expected. Its
[`/code-comments:stale-refs`](../../plugins/code-comments/commands/stale-refs.md) lint finds
comments that name code which no longer exists. It never compares values, and it reads
Markdown only to collect known names; research.md confirmed both on a scratch fixture (R5).

This skill adds:
1. **A list of old forms before searching:** digits with and without thousands separators,
   number words, the same quantity in other units (including hyphenated adjectives), and every
   figure derived from the old value. A search for the literal misses the other forms.
2. **A search of all the prose,** in every module and every doc, not only the edited files.
3. **A script that does that search,** `value_drift.py`, which matches digits, number words and
   round unit conversions. Nothing in the plugin or the prior art we found compares values in
   prose ([research.md](research.md), Finding 1).
4. **A sort for every hit:** living description (correct only the false clause), record (keep
   word for word), outside fact (keep and report), instruction file (report), unrelated (leave).
   The shipped skill has the outside-fact rule but nothing that protects records.
5. **Correction rules for derived figures:** recompute them from the code, keep the sentence's
   own form, leave pointer comments alone, and report drift the change did not cause.
6. **For renames and moves,** the Markdown that stale-refs skips: backticked names, fenced
   examples and relative link targets.

It does not repeat the shipped skill's writing rules. When both are installed, the shipped
skill governs how each correction reads.

## When to use it

Use it before finishing any edit that gives a new value to a constant, default, limit, timeout,
interval, count, size or unit, or that renames or moves a flag, config key, option, function or
file. This holds even when the request never mentions comments or docs. Also use it when someone
asks which docs a change affects.

Do not use it for:
- reviewing a finished diff that someone else wrote (the review mode is a next step);
- writing new docs, or retiring a docs page (that is [fold-docs-inline](../fold-docs-inline/README.md));
- comment wording in general, or a change that touches no stated value or name (the shipped
  skill covers these).

## How it works

The skill is instructions plus an optional script. It works without the script: SKILL.md gives a
`grep` recipe for the same forms.

1. **List the old forms:** digits, number words, other units, derived figures, and old names or
   paths.
2. **Search all the prose,** with the script or with grep.
3. **Read and sort every hit.** Only a sentence about the changed thing is changed.
4. **Correct the living hits.** Recompute derived figures from the new code.
5. **Reply** with what was corrected, what was kept and why, and drift the change did not cause.

### The script

```sh
python <skill folder>/scripts/value_drift.py <repository root> --old "7200 s" --new "10800 s" --old 12
```

- **Input.** `--old` repeats: pass the old value and each derived figure, since the script
  cannot compute those. A number can carry its unit (ms, s, min, h, day, week, B, KB, KiB, MB,
  MiB, GB, GiB, TB, TiB); `--unit` sets one for numbers without. Anything that is not a number
  (a flag, key, name or path) is matched as bounded literal text. `--new` prints the new value
  in each unit and marks the lines that already state it. `--near REGEX` keeps only hits whose
  line, or the prose line just before or after it, matches REGEX (SKILL.md asks for it below
  10). `--near` and `--unit` apply to every `--old` in the call, so SKILL.md asks for a
  value under 10 to be searched in a call of its own (v2). `--strings` also reads string
  literals in code. `--json` prints the hits as JSON.
- **What it reads.** Python comments and docstrings (by `tokenize` and `ast`, so code literals
  are skipped), `//`, `/* */` and `#` comments in other languages and config files (all three
  in Terraform files since the review after the runs), and every line of Markdown and text
  docs. With `--strings`, also the string literals of code (help text, error and log
  messages), labelled `string`. Lines inside fenced blocks are labelled `fenced`. It skips
  caches, `.git`, `node_modules` and its own folder. Since that review it also lists what
  it skips that could hold prose: `build/`, `dist/` and `*.egg-info` folders at any depth,
  and files over 2 MB, under "not read" (`not_read` in `--json`). A listed folder can be
  swept by passing it as ROOT. A file that is not UTF-8 is read with replacement
  characters and listed as such. The runs used the script before these changes, which
  dropped those files and folders without a word.
- **Wrapped lines (v2).** Each prose line is read together with the next line of the same
  comment, docstring, string or paragraph, so a form wrapped across a line break is found.
  It is listed at the line where it starts. Two lines are not joined across a blank line, a
  new list item, quote, table row or heading. A line that ends in a hyphen joins without a
  space. A number at a line end is judged by the unit that starts the next line.
- **What it matches.**
  - Bounded digits, so 24 does not match 240, 2.4, 2024 or 24,000. ISO dates, clock times,
    version strings and issue numbers (`#4`) are masked first, so 30 does not match
    2026-06-30 or 02:30.
  - Number words, including hyphenated and "and" forms, but not a word inside a larger number
    ("five" in "twenty-five"). Since the review after the runs, also a whole number and a
    half ("two and a half minutes" for 150 s), and no longer "two" inside it for 2 min.
  - Round conversions to other units of the same family, matched only with a unit beside them,
    so a stray "45" is not read as 45 minutes. A number word needs a space or hyphen before its
    unit, so "ones" is not one second.
  - When the value has a unit, a bare number followed by a different unit is skipped: for 7 s,
    "7 days" is not listed.
  - A few idioms: "half an hour", "a quarter of an hour", "an hour and a half", "twice",
    "a dozen", and "a second", "a day" or "an hour" after a time word ("after a second"). So
    "a second request" and "10,000 calls a day" are not listed.
  - Sizes are read both as 1,000 and as 1,024.
- **Output.** `path:line: where [hints]: "form" = value: text`. The hints are `record?` (a
  changelog, ADR, decision, migration, incident or dated file, guessed from the path),
  `instructions?` (AGENTS.md, CLAUDE.md and the like) and `states new`. They decide nothing.
- **Exit status:** 0 whether or not it finds hits, 2 for a usage error. `--check` exits 1 on
  hits, for CI. Before the review it exited 1 on hits, which an agent's shell shows as a tool
  error.
- **No state.** It reads the files fresh on every run, writes nothing and stores nothing, as
  [ADR 0001](../../docs/adr/0001-context-lives-inline-no-central-index.md) allows for mechanical
  checks. It uses only the Python 3.10+ standard library.

The unit tests cover:
- word bounds, thousands separators, and masked dates, times, versions and issue numbers;
- number words, and larger-number exclusion;
- unit conversions, a different unit after a bare number, the separator before a word's
  unit, and idioms with and without a time word;
- both size readings, and literal flags and paths;
- what each file type reads, with and without `--strings`;
- forms wrapped across a line break, the unit on the next line, and where lines are not
  joined;
- `--near`, the path hints and the exit codes;
- that no file is written, and that the script's own folder is skipped.

```sh
cd incubator/change-drift-sweep/skill/change-drift-sweep/scripts
python -B -m unittest     # 41 tests (36 when the runs used it)
```

The script and one SKILL.md bullet changed after every run, in review fixes listed in
[eval/CHANGES.md](eval/CHANGES.md) ("After the runs"). No run used those changes. The
version each run read is in its iteration's `skill-snapshot/`, and the results above
are for those snapshots.

On this repository's `docs/` folder, `--old 3` lists 1,114 prose lines. Adding
`--near "retr|attempt|tries"` brings that to 53. v1 and v2 give the same counts. These
counts are from 2026-11-11.

## Where each rule comes from

Grades:
- **measured:** an experiment or a mining study;
- **practitioner:** expert or vendor guidance;
- **repo-eval:** this repository's own runs or fixtures;
- **hypothesis:** no source tests it;
- **judgement:** the skill writer's choice, named so it can be challenged.

The R and W ids are research.md's sources.

| Rule in SKILL.md | Source | Grade |
| --- | --- | --- |
| Sweep before the final reply after any edit that re-values, renames or moves something, even when the request never mentions docs | R1 ("only reading catches it"); R5 (stale-refs ignores values and Markdown prose, confirmed on a fixture); W1 (Tan et al.: names only); W2 (docs trail code in agent PRs). The trigger list itself is untested | problem measured; behaviour hypothesis |
| List the old forms first: digits with and without separators, number words, every other unit and hyphenated adjectives | W11 (Microsoft spells out zero to nine and uses commas in four-digit numbers); W12 (Google uses numerals for technical quantities); W7 (LLMCup did worst on edits that "lack code anchoring") | practitioner; that the list raises recall is a hypothesis |
| Derived figures, worked out from the old code; they may not contain the old value | R3 (the one recorded value-drift miss left "2, 4 and 8" and "14 seconds", which never contain 3) | repo-eval (one run in 33) |
| For a rename or move, list the old name in backticks, fenced examples and link targets | R5 (a renamed flag in a Markdown doc survived stale-refs on the fixture) | repo-eval (tool gap on a fixture) |
| Search all prose, not only the edited files | R3; R6 (comments on callers and interfaces lag); W1; W2 | practitioner / repo-eval |
| The script reads fresh, writes and stores nothing, and decides nothing; it cannot compute derived figures | R10 (ADR 0001 allows checks that read the code); the coordinator's direction; W9 (false positives are the main cost of detectors) | design constraint |
| For a value under 10, narrow the hits with `--near`, in a call of its own (v2) | W9; the 2026-11-11 review (`--old 3` listed over 1,000 lines on this repository's docs); iteration 1 (one Haiku run's shared call dropped a derived-figure line) | repo-eval (hit counts; one run); that it keeps recall is a hypothesis |
| Without the script, grep the same forms | The coordinator's requirement that the skill works without the script | design constraint |
| User-facing strings (help text, error and log messages) are living descriptions; `--strings` reads them | The 2026-11-11 review: they describe the current value to users, and the old fallback told the agent to drop them | judgement |
| Change a hit only when its sentence is about the changed thing; leave unrelated facts that share the number | R8 P-26 ("Code that only coincidentally matches is not duplication"); W9 | practitioner |
| Living description: correct only the false clause, the rest word for word | R2 (the shipped skill: check each clause, leave valid comments word for word) | practitioner / repo-eval |
| Record: keep word for word | W13 (Keep a Changelog: entries per version); W14 (Nygard: superseded, not rewritten); R7. Counterevidence: W13's FAQ invites improving entries; P-29 (Parnas) rewrites design documents | practitioner, contested |
| A page that says how the code works now is living wherever it sits; `record?` is a guess | Finding 8 (which documents count as living is a judgement) | judgement |
| Outside fact: keep it, report a conflict | R2 (the shipped skill's outside-fact rule); R4 (the reminder deleted a true quota in 3 of 5 runs) | repo-eval |
| Instruction file: leave it unless asked, report the line and its replacement | Candidate C3 behaviour (e); the same treatment in fold-docs-inline and verify-before-relying; research open question 5 | candidate; open question |
| If the change contradicts an ADR, keep it and say it may need superseding; a changelog line only under an existing `Unreleased` heading | W14; W13 ("Keep an `Unreleased` section at the top"). Whether to add a line at all is research open question 4 | practitioner |
| Recompute derived figures from the new code, with arithmetic or a one-line snippet | R3 (the run that missed the comment computed the doc's total right) | hypothesis |
| Keep the sentence's own form (a word stays a word) | Close to the shipped skill's "Fit in" | judgement |
| Where a copy only restates a constant, naming the constant is also a correction | R2 (the shipped skill: "Give each fact one home. Point to it rather than copy it") | practitioner |
| A pointer comment that names the constant without its value needs nothing | R2 ("the source of a constant, not its copied value"); P-27; P-29 | practitioner |
| State the current value only; history belongs in the commit | R2 ("Describe the current design, not its history") | practitioner |
| Drift the change did not cause: always report it with both values; leave it, or correct only its figure toward the code; never change the code to match it unasked | For correcting: R10 (ADR 0001: "The code is the source of truth. It is what runs.") and R2 (the shipped skill: "Treat existing comments as claims. Check them against the code"). For leaving: R9 (code consistency alone cannot decide which side is wrong). Research design rule 8 said "do not fix it"; the review of 2026-11-11 found the project's own sources support correcting, so both are allowed | judgement, contested; open question |
| For a rename or move, also run stale-refs, and check that changed links resolve | R5 | repo-eval (tool gap on a fixture) |
| Done when every form is searched, every hit is sorted, and no living description still states the old value | A checkable completion criterion (writing-for-agents) | judgement |
| The reply lists corrections, kept records and outside facts, and pre-existing drift | R2; in the hygiene eval, reply duties separated the arms most clearly | repo-eval |

The eval did not move any rule's grade to measured. It did not separate the skill from the
reminder or the shipped skill on any behaviour these rules cover (see Results).

### Provenance of the text

SKILL.md and the script were written from research.md, the C3 and C7 candidates and the
judges' scores, before any eval file was read. The writer then read `eval/arms.json` and
`eval/CASES.md` to write this README, and made three changes so that no example matches a case:
- the flag in SKILL.md's dash example became `--legacy`;
- the arithmetic example became `86400 // 10800`, because the first one happened to compute a
  figure that one case grades;
- the script's docstring and unit tests now use neutral values.

No other rule changed. The `cases/`, `references/` and `hidden/` folders were not opened.

The writer's note does not say which case the first arithmetic example matched, and the
first example was not kept. The replacement computes a per-day count. The only case that
graded a per-day count was `poll-interval-per-day`, a held-out case, so a held-out case most
likely decided that edit. That breaks the incubator rule that held-out cases never decide a
skill edit. The review of 2026-11-11 found this. In response:
- that case was replaced with one no skill writer has seen;
- the held-out cases moved out of `eval/CASES.md` into `eval/HELD-OUT.md`, which skill
  writers do not read.

**Edits after the review (2026-11-11).** A fixer changed SKILL.md and the script from the
review's findings, adding nothing taken from the cases:
- **Pre-existing drift.** The rule changed from "report it and leave it". It is now: always
  report it; leave it, or correct its figure toward the code.
- **`--near`.** Use it for values under 10.
- **User-facing strings.** They count as living descriptions, and the script gained
  `--strings`.
- **Pointer corrections.** Naming the constant is now an accepted correction.
- **Exit status.** The script exits 0 on hits; `--check` exits 1, for CI.
- **Fewer false hits.** Dates, clock times, versions and issue numbers are masked, a
  different unit after a bare number is skipped, number words need a separator before
  their unit, and "a second", "a day" and "an hour" need a time word before them.
- **One new idiom:** "an hour and a half".

One script finding came from running it on a training case: for 7 s it listed "7 days" in
`derived-backoff-total`. The other probes were hand-written lines. No held-out case informed
a script or SKILL.md change.

**Edits after iteration 1 (v2).** Two changes came from misses in the search step of Haiku
`with_skill` runs, though every run still passed every check
([eval/CHANGES.md](eval/CHANGES.md)):
- the script reads each prose line with the next line of its block, because it left out
  an idiom wrapped across a docstring's line break in 3 of 3 runs of one case;
- SKILL.md asks for a value under 10 in a call of its own, because one run's `--near`
  dropped a derived-figure line from a shared call.

The held-out cases were not opened for v2. One recursive directory listing printed their
file and grader file names.

research.md is the record of the first design and was not changed. Where it differs, this
README and SKILL.md hold:
- its design rule 8 ("report it, do not fix it") is the old pre-existing-drift rule;
- its note on which cases are held out names the replaced case.

## The eval

[eval/CASES.md](eval/CASES.md) has the full design. In short:
- **Cases:** seven small Python repositories with unittest tests. Five are for training and
  two are held out (`held_out: true` in `case.yaml`). The training cases cover:
  - a changed default stated in digits and as a number word;
  - a value that prose states only in another unit;
  - derived figures (waits, totals and a product);
  - a flag rename with records that must stay byte-identical;
  - drift that predates the change, which must be reported whether or not it is corrected.

  The two held-out cases are a restraint guard and a generalisation check. Only
  [eval/HELD-OUT.md](eval/HELD-OUT.md) describes them, and a skill writer does not read it.
- **Prompts** read as a user would write them and, unlike the hygiene eval's, list no input
  files.
- **Arms:**
  - `with_skill` reads this skill and may run its script;
  - `shipped_skill` reads the shipped hygiene skill;
  - `reminder` adds the sentence in [eval/arms.json](eval/arms.json), which names number words,
    unit conversions, derived figures, records and outside facts;
  - `without_skill` gets the request alone.
- **Graded:**
  - core: hidden tests, including neighbouring settings that share the number; prose checks
    that the old value is gone and that every changed sentence gives the right new figure;
    the fixture's own tests;
  - preservation and restraint: byte-identity for records and outside facts, a line-order
    check that leaves released changelog sections untouched and puts new lines under
    `[Unreleased]`, and `lost_prose` for every other accurate line;
  - reply: one check, in the pre-existing-drift case, which needs its cues in one paragraph
    with a contrast.

  Sentence-level checks are heuristics; a misgrade gets an `overrides.json` ruling.
  `eval/test_grade.py` pins the checks with 107 graded variants: 34 good results, 72 bad
  ones and 1 known misgrade (a true `unit-spelled-ttl` sentence that check 02 fails).

The reminder nearly states the list of forms and the sorting rule in one sentence, and it also
asks for mismatches the change did not cause to be reported. A tie on the core checks is the
expected result. The skill has the most room to differ where the reminder says nothing:
- unrelated facts that share the number;
- pointer comments, and naming the constant as a correction;
- changelog lines only under `Unreleased`;
- recomputing derived figures from the code rather than editing them by analogy.

It did not beat the reminder or the shipped skill. That null result is under Results.

The `shipped_skill` arm reads only the shipped SKILL.md (`harness.SHIPPED`). It does not get
the `/code-comments:stale-refs` command. So the eval cannot test whether "the shipped skill plus
stale-refs" matches this skill. In six of the seven cases that gap makes no difference:
stale-refs compares no values (research R5, confirmed on a fixture), so it would add nothing
there. Only in `flag-rename-records-stay` could stale-refs help, and only for code comments; it
skips the Markdown that carries most of that case. If the shipped arm ties this skill on that
case, or on all of them, the skill is a plugin enhancement (#21, #48), not a new skill. Giving
that arm the stale-refs script path in the rename case is an open step.

## Results

165 graded runs:

| Run set | Runs |
| --- | --- |
| Iteration 1 (v1, training, all arms) | 100 |
| Iteration 2 (v2, training, `with_skill` only) | 25 |
| Held out (v2, all arms) | 40 |

What else applies to these runs:
- **Gate runs.** The 21 gate runs are not counted.
- **Exclusions.** Four iteration-1 runs were excluded and re-run, because the run-limits
  guard misread their shell commands. An auditor agent decided this after the runs; the
  rule written before the eval excluded only skill-arm runs that skipped the skill read.
  Two Haiku runs that the guard stopped from writing a reply were kept, because their
  cases do not grade the reply.
- **Skill reads.** Every skill-arm run read its skill before its first edit.
- **Rulings.** The numbers include three rulings by auditor agents, all turning a
  heuristic fail into a pass: two for `with_skill` in iteration 2, one for the shipped
  skill in iteration 1.

Mean pass rate and checks passed, from `harness.py summary`:

| Iteration | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `iteration-1-haiku` (v1) | 100.0%, 96/96 | 98.9%, 95/96 | 100.0%, 96/96 | 91.3%, 88/96 |
| `iteration-1-sonnet` (v1) | 100.0%, 64/64 | 100.0%, 64/64 | 98.3%, 63/64 | 98.6%, 63/64 |
| `iteration-2-haiku` (v2) | 100.0%, 96/96 | not run | not run | not run |
| `iteration-2-sonnet` (v2) | 100.0%, 64/64 | not run | not run | not run |
| `heldout-haiku` (v2) | 100.0%, 36/36 | 97.2%, 35/36 | 100.0%, 36/36 | 94.4%, 34/36 |
| `heldout-sonnet` (v2) | 100.0%, 24/24 | 100.0%, 24/24 | 100.0%, 24/24 | 95.8%, 23/24 |

Core checks passed, both models together:

| Split | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| Training, iteration 1 (v1) | 100/100 | 100/100 | 99/100 | 92/100 |
| Training, iteration 2 (v2) | 100/100 | not run | not run | not run |
| Held out (v2) | 30/30 | 29/30 | 30/30 | 27/30 |

What the numbers show:
- **Against the reminder and the shipped skill: a tie.** Over iteration 1 and the
  held-out pair, the skill passed 220/220 checks (v1 in training, v2 held out), the
  reminder 219/220 and the shipped skill 218/220. Each miss is one run:
  - the reminder left "fifteen minutes" in one Sonnet docstring;
  - the shipped skill's Haiku reply left out the pre-existing flush mismatch once;
  - the shipped skill wrote one ambiguous gloss on held-out Haiku.
- **By this README's own test, the skill is a plugin enhancement, not a new skill.** The
  section above said so if the shipped arm tied on `flag-rename-records-stay` or on every
  case. It tied on the rename case (every run full marks), and came within one run of the
  skill on every other case.
- **Against the bare model: a gain on Haiku only.** Haiku training: 96/96 against 88/96.
  All 15 skill runs passed every core check, against 9 of 15 bare runs (two-sided Fisher
  p = 0.017, chosen after reading the runs). The test treats runs as independent, but the
  6 bare shortfalls are all 3 runs of each of 2 cases. The bare misses were:
  - a wrapped quarter-hour idiom, or a "fifteen minutes" docstring and a banner time
    (`unit-spelled-ttl`);
  - two figures worked out from the old batch size (`pre-existing-drift-reported`);
  - a note added to an accepted ADR.

  On Sonnet the bare model scored 63/64 and 23/24.
- **The held-out pair, the main test of whether it generalises.**
  - **Carried over:** every `with_skill` run in `poll-interval-average-wait` corrected
    both averages derived by halving (5/5). That form is not on SKILL.md's list, and one
    of the averages sits in a module that never names the setting. Every run in every arm
    kept the dated incident entry inside the living page.
  - **No gain over the others:** the reminder did the same in 5/5 runs, and the shipped
    skill corrected both averages in 5/5. The bare model left one average stale in 2 of
    5 runs.
  - **The restraint guard held:** in `pointer-comment-needs-nothing` every skill run
    changed only the constant, so the skill did not cause over-editing.
- **v2 fixed its script target and changed no score.** The script now lists a form
  wrapped across a line break. It did so in both iteration-2 runs that ran it before
  editing. The `--near` change could not be tested: every run passed every check, so a
  dropped hit cost nothing.
- **No traced fix came only from a script hit.** Haiku ran it in every skill run, Sonnet
  in 4 of 24. Each traced run had read the files first. The trace left out 20 of the 25
  iteration-2 runs, and no arm had the skill without the script, so the script's effect
  was not measured.
- **Ungraded differences.** Most favour the skill over the bare model and the shipped
  skill, but not over the reminder:
  - it never created a changelog section where none existed; the bare model did in 9 of
    10 runs on the two cases without one;
  - it never added a comment beside the changed constant; the shipped skill did in 4
    cases;
  - on Haiku it kept "a hundred" as words ("two hundred and fifty").
- **Cost: longer replies and, on Haiku, more tool calls.** The skill's replies were the
  longest in every iteration: held out, 222 words on Haiku against 201 for the reminder
  and 136 bare. On Haiku it made the most tool calls and used the most output tokens.

The full tables, every failure and the cost figures are in
[eval/RESULTS.md](eval/RESULTS.md).

## Running the eval

From the repository root:

```sh
python incubator/harness.py lint change-drift-sweep
python incubator/harness.py self-test change-drift-sweep
# Gate: the bare arm first, on both models (the recorded gate ran all seven cases,
# the held-out pair included; see Limits)
python incubator/harness.py prepare change-drift-sweep --iteration gate-haiku --arms without_skill --runs 2
# Then the training split with all four arms
python incubator/harness.py prepare change-drift-sweep --iteration iteration-1-haiku --runs 3 --split train
#   give each prompt in eval/iterations/iteration-1-haiku/runs.json to a fresh agent of the chosen model
python incubator/harness.py grade change-drift-sweep --iteration iteration-1-haiku
python incubator/harness.py verify-reads change-drift-sweep --iteration iteration-1-haiku TRANSCRIPT_DIR
# After a skill edit, re-run the skill arm only, under a new iteration name
python incubator/harness.py prepare change-drift-sweep --iteration iteration-2-haiku --arms with_skill --runs 3 --split train
# Once, at the end: the held-out cases
python incubator/harness.py prepare change-drift-sweep --iteration heldout-haiku --runs 3 --split held-out
python incubator/harness.py summary change-drift-sweep iteration-1-haiku iteration-1-sonnet iteration-2-haiku iteration-2-sonnet heldout-haiku heldout-sonnet
```

Further steps:
- Run the held-out cases only once, at the end, under their own iteration name.
- Exclude and re-run any skill-arm run that `verify-reads` reports as not reading the skill
  before its first edit.
- Exclude and re-run any run the run-limits guard stopped before it wrote something its
  case grades: its edits, or `RESPONSE.md` in a case with a reply check. Keep, and grade as
  it stands, a run the guard stopped only from writing a reply its case does not grade.
  This rule was written after the iteration-1 runs. It covers the four excluded runs and
  the two kept ones (see eval/RESULTS.md, "Excluded runs").
- For each `with_skill` run, note from the transcript whether `value_drift.py` ran, what it
  listed, and whether any fix came only from a script hit. This separates the script's value
  from the instructions' value.

## Limits

Of the eval:
- **Few runs.** 2 or 3 runs per cell detect only large effects. Two-sided Fisher exact
  p-values:
  - 3/3 against 0/3: 0.10;
  - 5/5 against 2/5: 0.17.

  Every gap between the skill, the reminder and the shipped skill is one run. Totals pool
  checks that one decision can fail together, so they describe the runs; they are not
  tests.
- **Small fixtures.** Seven small Python repositories of 9 to 13 files, one case per
  behaviour and one phrasing per request.
  - Every run could read every file, and nearly all did. So the eval cannot measure the
    search step or the script, which matter only when a repository is too large to read.
  - The script did not flood here: before any edit it listed 2 to 12 lines. A
    number-heavy repository may differ.
- **One model family.** Claude Haiku and Sonnet only. The transcripts record
  `claude-haiku-5-5` and `claude-sonnet-5-5`; the harness itself stores no model id.
- **Cases built by agents.** Every case, reference, grader and hidden test was written by
  an agent. None comes from a real repository or a user's report.
- **Rulings made by agents.** All three rulings (`overrides.json`) were made by auditor
  agents, not a human. Two credited the skill's own replies. The reply check's contrast
  cues lack "false" and "drift", the words SKILL.md's reply rule leads to. Without the
  rulings, v2 would trail v1 by one check on each model.
- **Gate-based case selection, hardened without a re-gate.**
  - A bare-model gate ran first on all seven cases, the held-out pair included. Four
    training cases and one held-out case were at ceiling and were hardened
    ([eval/GATE.md](eval/GATE.md)).
  - The gate was not re-run on the hardened fixtures. The iteration-1 bare arm was the
    first measure. It showed headroom on Haiku in two of the four hardened training cases
    and on Sonnet in none. `derived-backoff-total` stayed at ceiling for every arm. In
    the held-out run, the hardened held-out case, `poll-interval-average-wait`, showed
    headroom on both models: 2 of 5 bare runs had full marks (one Haiku shortfall is the
    ambiguous gloss).
  - Selection by a bare gate favours cases where the bare model falls short. It does
    not favour cases that separate a skill from a good reminder.
- **Held-out exposure.**
  - No skill edit drew on the current held-out pair, and its contents were not opened for
    v2. The held-out case it replaced, `poll-interval-per-day`, most likely decided one
    edit (see Provenance).
  - The pointer case was described in CASES.md when the skill was first written, so it
    is a restraint guard, not a clean test.
  - The v2 writer's directory listing printed the held-out file and grader file names,
    such as `03-average-wait-recomputed.md`.
- **Prompt read from a file.** Each agent read its task from `prompt.txt` as its first
  tool call. A real request arrives as a user's message.
- **Activation is untested.**
  - The eval tells the skill arms to read the skill first, so it says nothing about
    whether the description makes the skill load on its own.
  - On its own, the shipped skill loaded in 0 of 18 Haiku and 3 of 18 Sonnet
    should-load runs (#20).
- **The shipped arm had no stale-refs.** It read the shipped SKILL.md only. It tied anyway.
  That adding stale-refs would only help it is a hypothesis; no run tested it.
- **Iteration 2 is compared across runs.** v2 ran only `with_skill`, and is compared with
  the other arms' iteration-1 runs.
- **Keyword checks.** The sentence and reply checks are heuristics. The auditors read every
  failed check and every passing heuristic result in every arm. A paraphrase can still
  slip through.
- **Some behaviours are ungraded:** new changelog sections, unrequested comments,
  renamed internal parameters and number word form. Their counts come from the writer's
  reading of the diffs, and can be recounted from each run's committed `changes.diff`.
  Tool calls, tokens, script use and Edit errors come from transcripts, which are not in
  the repository.

Of the skill:
- **No gain over a one-sentence reminder is shown.** On these cases the reminder in
  [eval/arms.json](eval/arms.json) did as well, with shorter replies.
- **The record boundary is a policy, not a fact.** Keep a Changelog allows improving old
  entries, and Parnas would rewrite a design document to read as the new design. A misjudged
  record leaves a living doc false; a misjudged living doc rewrites history. The user should
  confirm the rule. No run in any arm rewrote a record the checks protect. The one record
  edit was a note a bare Haiku run added to an ADR.
- **Number forms are open-ended.** The script misses:
  - rates and frequencies ("twice a day" for a 12-hour interval);
  - conversions that do not come out round (0.0625 MiB);
  - ordinals, fractions other than a half or a quarter, and prose in other languages;
  - Before the review after the runs, "two and a half minutes" from 150 s or 2.5 min. The
    held-out runs scored that earlier script: only reading found that sentence, except in
    the one run that passed the phrase itself. The script now lists it, so
    `poll-interval-average-wait` no longer tests this gap blind.

  Reading cannot recover a form nobody listed.
- **Small values still flood without `--near`.** An old value of 1, 2 or 3 matches many
  unrelated lines, and the agent has to read each one. In a number-heavy repository that load
  could push edits onto unrelated numbers (W9). `--near` cuts the list, but it also drops a
  true hit whose sentence never names the subject. In iteration 1 that happened once, in a
  call that mixed a small value with a derived figure. v2 asks for a separate call. No run
  has measured the trade-off in a call of its own.
- **String literals are read only with `--strings`.** Help text, log messages and error strings
  describe values too. Tests may pin them.
- **Path hints are guesses.** A record with an unusual name gets no `record?` hint. So does a
  dated section inside a living page. A living page in a dated folder gets one.
- **Relative links are matched as written.** A link to `docs/old.md` written from inside
  `docs/` reads `old.md` or `./old.md`. Pass each spelling as its own `--old`.
- **Other languages are read heuristically** (`//`, `/* */` and `#` comments). reST code blocks
  are not labelled as fenced.
- **Longer replies.** The skill's replies were the longest of all arms in every iteration.
  On Sonnet part of the length may be sentences that report an empty category ("no ADR
  or instruction file ..."), found in 10/10 iteration-1 skill replies. On Haiku more of
  the reminder's replies had one (10/14 against 5/14). v2 did not address this.

## Next steps

The gate, the four-arm run, one revision (v2) and the held-out run are done. In order:

1. **Put the null result to the user.**
   - The graded data support the skill over the bare Haiku model only. They do not support
     it over the reminder sentence in [eval/arms.json](eval/arms.json) or the shipped skill.
   - Do not move the skill into a plugin unless the user decides to.
   - Offer the user three options:
     - use the reminder sentence;
     - fold the parts the shipped skill lacks into it as a plugin enhancement (#21, #48):
       the list of old forms, derived figures, and the record rule;
     - keep this skill only if a case that needs the search step separates it (step 2).
2. **Build cases that need the search step, if the user wants the skill tested further.**
   The current fixtures let every run read every file.
   - Build 2 or 3 training cases with repositories too large to print whole, for example
     150 or more files. Put the stale statements in files that never name the setting.
   - Gate them on the bare model (Haiku x3, Sonnet x2) and keep cases with bare failures.
     Also run the reminder arm in the gate, and keep only cases where the reminder misses
     too.
   - Run all four arms with 5 or more runs per cell. Record per run whether a fix came
     only from a script hit.
   - Build a fresh held-out pair, and run it once.
3. **Fix the grader gaps in `eval/grade.py`**, each with a `test_grade.py` variant:
   - `_C1_LIMIT_BEFORE`: add "above";
   - `_C5_CONTRAST`: add "false" and "drift", the words SKILL.md's reply rule leads to;
   - `poll-interval-average-wait` check 02: decide how to grade "half a poll interval
     (ten minutes)", and pin it.

   Then run `python incubator/harness.py self-test change-drift-sweep`, re-grade every
   iteration with `harness.py grade`, and check whether each `overrides.json` ruling is
   still needed. Keep the rulings as a record.
4. **Harness fixes**, all in `incubator/harness.py`:
   - Done after these results: `verify-reads` now counts each tool call once, by id. The
     committed change-drift-sweep `verify-reads.json` files already counted that way.
   - When a run was excluded and re-run at the same outputs path, `verify-reads` reports
     whichever transcript sorts last. Report every match, or the latest one. In the
     committed files this names the excluded original for all three re-run skill-arm
     runs.
   - Make `verify-reads` store its result in the iteration folder.
   - Record the model id from the transcript in each run's grading.
   - Tell run agents to edit files and write RESPONSE.md with the file-writing tools, at
     the absolute path the prompt gives. The run-limits guard misread `sed -i` and heredoc
     commands in four runs, and a Write to a path respelled `/tmp/...` in two more.
5. **Test the shipped skill with stale-refs** only if step 2 goes ahead. Give the
   `shipped_skill` arm the stale-refs script path in the rename case. It tied without it.
6. **Ask the user the open questions:**
   - Drift the change did not cause: correct it toward the code and report it, or report
     it and leave it? Both are allowed. v2 Sonnet corrected the flush figure in 2/2 runs,
     and every other run left it.
   - Where does the living/record line fall, for design docs in particular?
   - Should the agent add an `Unreleased` changelog line, or leave changelogs alone? The
     bare model created a new `Unreleased` section in 9 of 10 runs on cases without one.
     The skill and the reminder never did.
   - Should instruction files stay report-only?
   - Should a size match both the 1,000 and the 1,024 readings, or only the unit the prose
     states?
7. **Reply length, if the user finds it too long.** Try one rule on the training cases:
   leave out reply items with nothing to report. Measure words, and check that the reply
   check does not regress.
8. **Review mode for finished diffs (candidate C7)**, only if the user still wants it.
   v1 and v2 act on the agent's own edit. The next mode would review a diff someone else
   wrote, often a human editor who never ran the edit-time skill. It would:
   - take `--base-dir DIR` or `--diff REV`, like stale-refs, and derive the changed values and
     names from the base and head trees;
   - reuse `value_drift.py`'s form matching, so there is one detector, as all three judges
     asked;
   - list prose outside the hunks that still states an old value, change no file, and report
     each finding as path and line;
   - be graded from a machine-readable findings file against planted stale lines and true
     decoys, including a consistent diff that should produce no findings;
   - use two-commit fixtures built by `place-files.sh`, with read-only git allowed and the
     deviation recorded.

   The skeptic judge counted about ten installed review skills competing for activation, so it
   should ship command-first. A review mode faces no "read everything" shortcut on a large
   diff, so it may show the script's value where the edit-time skill could not.
9. **Decide where the Markdown checks live.** The link-target and fenced-example checks for
   renames may belong in stale-refs (#21, #48) rather than here.
10. **Reserve cases**, for step 2 or the review mode:
    - a TypeScript JSDoc and README case (a size in MB written in bytes);
    - Markdown link targets after a move;
    - a default argument whose figure another module states without naming it;
    - a KB or MB case for the 1,000 or 1,024 question;
    - a living page filed in a dated folder, which the script wrongly marks `record?`;
    - an argparse `help=` string that states the old default, which only `--strings` or a
      grep finds.
11. **Before any shipping decision:**
    - run an activation eval with near misses (a question about a value, a release note,
      a refactor that changes no value);
    - add an arm with both this skill and `code-comments` loaded, since that is how they
      would ship;
    - use a model outside the Claude family;
    - add a command, so a person or CI can run the script without an AI run.
