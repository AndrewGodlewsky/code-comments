# change-drift-sweep

A candidate skill for the moment just after a change gives something a new value, name or
place. It finds every comment, docstring and Markdown doc that still states the old value,
in any form, corrects the ones that describe the code, and keeps the ones that are records
or outside facts.

**Status: built; evaluation pending.** No run has been made, so there is no result to
report. The skill makes no performance claim. It is ideation candidates C3 and C7
([candidates](../ideation/2026-11-11-candidates.json)) for issue
[#50](https://github.com/AndrewGodlewsky/code-comments/issues/50), as narrowed by the
coordinator's direction, and it does not ship.

- Skill: [skill/change-drift-sweep/SKILL.md](skill/change-drift-sweep/SKILL.md)
- Script: [skill/change-drift-sweep/scripts/value_drift.py](skill/change-drift-sweep/scripts/value_drift.py),
  with its tests in `test_value_drift.py` beside it
- Research: [research.md](research.md)
- Eval design: [eval/CASES.md](eval/CASES.md)

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
the hygiene eval a one-line "fix what is false" reminder deleted a true vendor quota in 3 of
5 iteration-5 runs ([research.md](research.md), R4).

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
  10). `--strings` also reads string literals in code. `--json` prints the hits as JSON.
- **What it reads.** Python comments and docstrings (by `tokenize` and `ast`, so code literals
  are skipped), `//`, `/* */` and `#` comments in other languages and config files, and every
  line of Markdown and text docs. With `--strings`, also the string literals of code (help
  text, error and log messages), labelled `string`. Lines inside fenced blocks are labelled
  `fenced`. It skips caches, `.git`, `node_modules` and its own folder.
- **What it matches.**
  - Bounded digits, so 24 does not match 240, 2.4, 2024 or 24,000. ISO dates, clock times,
    version strings and issue numbers (`#4`) are masked first, so 30 does not match
    2026-06-30 or 02:30.
  - Number words, including hyphenated and "and" forms, but not a word inside a larger number
    ("five" in "twenty-five").
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
- `--near`, the path hints and the exit codes;
- that no file is written, and that the script's own folder is skipped.

```sh
cd incubator/change-drift-sweep/skill/change-drift-sweep/scripts
python -B -m unittest     # 33 tests
```

On this repository's `docs/` folder, `--old 3` lists 1,114 prose lines. Adding
`--near "retr|attempt|tries"` brings that to 53. These counts are from 2026-11-11.

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
| For a value under 10, narrow the hits with `--near` | W9; the 2026-11-11 review (`--old 3` listed over 1,000 lines on this repository's docs) | repo-eval (hit counts); that it keeps recall is a hypothesis |
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
  `eval/test_grade.py` pins the checks with 74 graded variants.

The reminder nearly states the list of forms and the sorting rule in one sentence, and it also
asks for mismatches the change did not cause to be reported. A tie on the core checks is the
expected result. The skill has the most room to differ where the reminder says nothing:
- unrelated facts that share the number;
- pointer comments, and naming the constant as a correction;
- changelog lines only under `Unreleased`;
- recomputing derived figures from the code rather than editing them by analogy.

If it does not beat the reminder and the shipped skill, that null result goes here.

The `shipped_skill` arm reads only the shipped SKILL.md (`harness.SHIPPED`). It does not get
the `/code-comments:stale-refs` command. So the eval cannot test whether "the shipped skill plus
stale-refs" matches this skill. In six of the seven cases that gap makes no difference:
stale-refs compares no values (research R5, confirmed on a fixture), so it would add nothing
there. Only in `flag-rename-records-stay` could stale-refs help, and only for code comments; it
skips the Markdown that carries most of that case. If the shipped arm ties this skill on that
case, or on all of them, the skill is a plugin enhancement (#21, #48), not a new skill. Giving
that arm the stale-refs script path in the rename case is an open step.

## Running the eval

From the repository root:

```sh
python incubator/harness.py lint change-drift-sweep
python incubator/harness.py self-test change-drift-sweep
# Gate: the bare arm first, on both models
python incubator/harness.py prepare change-drift-sweep --iteration gate-haiku --arms without_skill --runs 2 --split train
# Then the training split with all four arms
python incubator/harness.py prepare change-drift-sweep --iteration iteration-1-haiku --runs 3 --split train
#   give each prompt in eval/iterations/iteration-1-haiku/runs.json to a fresh agent of the chosen model
python incubator/harness.py grade change-drift-sweep --iteration iteration-1-haiku
python incubator/harness.py verify-reads change-drift-sweep --iteration iteration-1-haiku TRANSCRIPT_DIR
python incubator/harness.py summary change-drift-sweep iteration-1-haiku iteration-1-sonnet
```

Further steps:
- Run the held-out cases (`--split held-out`) only once, at the end, under their own
  iteration name.
- Exclude and re-run any skill-arm run that `verify-reads` reports as not reading the skill
  before its first edit.
- For each `with_skill` run, note from the transcript whether `value_drift.py` ran, what it
  listed, and whether any fix came only from a script hit. This separates the script's value
  from the instructions' value.

## Limits

- **No result yet, and no performance claim.** The cases are small, Python only, one per
  behaviour, and the runs will be few, on one model family.
- **Headroom is thin and unmeasured.** The one recorded value-drift miss is one Sonnet
  no-skill run in 33 distinct hygiene runs, and that prompt listed every file. Nothing yet shows
  bare models rewriting a changelog or an ADR. The gate is there to find out.
- **The record boundary is a policy, not a fact.** Keep a Changelog allows improving old
  entries, and Parnas would rewrite a design document to read as the new design. A misjudged
  record leaves a living doc false; a misjudged living doc rewrites history. The user should
  confirm the rule.
- **Number forms are open-ended.** The script misses:
  - rates and frequencies ("twice a day" for a 12-hour interval);
  - conversions that do not come out round (0.0625 MiB);
  - ordinals, fractions other than a half or a quarter, and prose in other languages.

  Reading cannot recover a form nobody listed.
- **Small values still flood without `--near`.** An old value of 1, 2 or 3 matches many
  unrelated lines, and the agent has to read each one. In a number-heavy repository that load
  could push edits onto unrelated numbers (W9). `--near` cuts the list, but it also drops a
  true hit whose sentence never names the subject. No run has measured that trade-off.
- **String literals are read only with `--strings`.** Help text, log messages and error strings
  describe values too. Tests may pin them.
- **Path hints are guesses.** A record with an unusual name gets no `record?` hint. So does a
  dated section inside a living page. A living page in a dated folder gets one.
- **Relative links are matched as written.** A link to `docs/old.md` written from inside
  `docs/` reads `old.md` or `./old.md`. Pass each spelling as its own `--old`.
- **Other languages are read heuristically** (`//`, `/* */` and `#` comments). reST code blocks
  are not labelled as fenced.
- **Activation is not measured.** The shipped skill loaded on its own in 0 of 18 Haiku runs and
  3 of 18 Sonnet runs (#20). This eval tells the model to read the skill.

## Next steps

1. **Gate.** Run `without_skill` on Haiku and Sonnet over the training split first. Drop or
   harden any case that every bare run passes. Paid runs need the user's approval, with the
   estimated and actual cost reported.
2. **Pilot** the training split with all four arms on both models. Grade it, check reads with
   `verify-reads`, record overrides, and compare `with_skill` against `reminder` and
   `shipped_skill` focus by focus. Report a tie or a loss as a result.
3. **Measure the script.** Count the runs where a script hit was the only route to a fix, and
   the script's false positives per fixture (research open question 2). Count how often
   `--near` was used, and whether it dropped a true hit.
4. **Test the shipped skill with stale-refs.** To test "the shipped skill plus stale-refs",
   give the `shipped_skill` arm the stale-refs script path in `flag-rename-records-stay`. Until
   then, the shipped arm stands for the shipped skill alone.
5. **Edit only from training-split failures,** then run the held-out split once.
6. **Ask the user** the open questions:
   - Drift the change did not cause: should the agent correct it toward the code and report
     it, or report it and leave it? The skill and the eval now accept both, and always ask
     for the report. ADR 0001 ("the code is the source of truth") favours correcting. R9
     (consistency cannot say which side is wrong) favours leaving.
   - Where does the living/record line fall, for design docs in particular?
   - Should the agent add an `Unreleased` changelog line, or leave changelogs alone?
   - Should instruction files stay report-only?
   - Should a size match both the 1,000 and the 1,024 readings, or only the unit the prose
     states?
7. **Review mode for finished diffs (candidate C7).** v1 acts on the agent's own edit. The next
   mode would review a diff someone else wrote, often a human editor who never ran the
   edit-time skill. It would:
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
   should ship command-first.
8. **Decide where the Markdown checks live.** The link-target and fenced-example checks for
   renames may belong in stale-refs (#21, #48) rather than here.
9. **Reserve cases:**
   - a TypeScript JSDoc and README case (a size in MB written in bytes);
   - Markdown link targets after a move;
   - a default argument whose figure another module states without naming it;
   - a KB or MB case for the 1,000 or 1,024 question;
   - a living page filed in a dated folder, which the script wrongly marks `record?`;
   - an argparse `help=` string that states the old default, which only `--strings` or a
     grep finds.
10. **If the user wants it in the plugin,** write activation cases with near misses (a question
   about a value, a release note, a refactor that changes no value). Also add a command, so a
   person or CI can run the script without an AI run.
