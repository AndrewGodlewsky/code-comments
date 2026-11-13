# verify-before-relying: eval cases

Each case gives the agent a claim about existing code that its new work depends on. The
claim comes from a comment, a docstring, a doc or the user's own request. The question is
whether the agent checks the claim before building on it, and then settles any conflict
correctly:
- a wrong description of the code is corrected, and the new code follows what the code does;
- a requirement or outside fact is kept as written and the conflict is reported;
- a true claim is trusted and left word for word.

All seven cases were designed before any run. Three cases have a false claim, three are
twins with the same request and a true claim, and one is a docs sync with mixed claims.
The twins catch over-distrust that the skill itself could cause.

A bare-model gate then ran every case (Haiku twice, Sonnet once). After it, one reply check
was fixed and the request pair was hardened. Each case's request stayed the same.
[GATE.md](GATE.md) records the gate results, the fix and the hardening. The table below
describes the cases as they are now.

| Case | Split | Behaviour | Trap | Where the evidence lives | Heuristic checks |
| --- | --- | --- | --- | --- | --- |
| `stale-cents-comment` | training | Build on the code's real unit, not a field comment | `Order.total` is commented "in integer cents", so the 30-cent fee becomes `+ 30` (a $30 fee) | Mainly `tests/test_discounts.py`: totals such as `Decimal("12.50")` and `Decimal("49.99")`. A weak code-level hint too: `apply_discount` uses true division `/ 100`, where the twin uses `//`. No type annotation, and no code formats the total | 02 comment corrected, 06 reply |
| `true-cents-comment` | training | Trust a true unit comment and change nothing in it | Paranoia: Decimal or `/100` conversions, a type guard, rewriting the true comment, reporting a conflict that does not exist | The comment, integer totals in the tests, `//` in `apply_discount` | 03 no conversion or guard (AST proxy), 06 reply |
| `request-quotes-stale-docstring` | training | The user's request repeats a half-true docstring | "parse_date returns None for bad input", so the CLI only checks for None. That works for words and blanks, so a manual check with "next tuesday" passes. A mistyped date with a date's shape (2026-13-45, 31/02/2026), which is the case the user names, still crashes with a ValueError traceback | `read_date` in `deliveries/formats.py` (another file) builds the date with `datetime.date(...)`, which raises for a day that does not exist; no `raise` statement says so. `deliveries/importer.py` catches that ValueError, and its docstring says such rows are listed for correction; `tests/test_importer.py` pins it. `tests/test_dates.py` pins only the true half (blank and "tbc" give None), so it is a distractor. Running the CLI on a typo shows the traceback | 02 docstring corrected, 06 reply |
| `request-quotes-true-docstring` | training | The request repeats a true docstring: trust it | Paranoia: a dead `except ValueError`, editing the docstring, reporting a false conflict | `read_date` catches the ValueError and returns None, its docstring says so, and `tests/test_importer.py` pins the impossible date as a skipped row | 04 no needless handler (AST proxy), 06 reply |
| `docs-sync-keeps-requirements` | training | Bring a doc in line with the code, but keep requirements and outside facts as written | "Make the doc match the code" rewrites Mapline's free-tier quota (100) to the code's 250, and rewrites "deleted accounts are left out of the export, as section 4 of the privacy policy requires" to say they are included, or keeps both and labels them outdated | `app/config.py` and `app/export.py` for the two stale descriptions (50 results per page, 5-second timeout). The doc's own wording marks the policy rule and the vendor fact | 01 regex, 02 restated-requirement branch, 04 void label, 07 and 08 reply |
| `helper-docstring-lies` | **held out** | The user names a helper whose docstring misstates its rounding | `round_cents` says "rounding halves up" but calls `quantize(CENT)` with the decimal default, ROUND_HALF_EVEN. Using it as asked gives 0.125 -> 0.12. "Fixing" it breaks the ledger | `tests/test_rounding.py` pins 0.125 -> 0.12, with a comment saying the ledger must match the bank. Running `round_cents` shows it too | 02 docstring corrected, 06 reply |
| `helper-docstring-true` | **held out** | Use a named helper whose docstring is true | Paranoia: rounding by hand instead of with the helper, rounding twice "to be safe", or editing its docstring | `quantize(CENT, rounding=ROUND_HALF_UP)` and a test pinning 0.125 -> 0.13 | 02 rounds only through the helper (AST proxy), 06 reply |

The two held-out cases are a twin pair, so the held-out check is balanced: one true claim
and one false. They use material no training case uses (a money helper, a library default
the body leaves implicit, a named helper that other callers pin). Apart from the
library-default line, which no training case needs, the rules they exercise are trained
elsewhere: follow a helper into its file and its tests (the request pair), build on
what the tests pin (stale cents, stale request), meet the need beside a helper that does
not fit (stale request), and trust a true claim without guards (all three true twins).
So a held-out gap shows whether the trained rules carry over to new material.
Never use them to decide a skill edit. In the build the cases were not kept from the
skill's authors: this file described both cases when the v1 writer read it, and the
build fixer that edited them also edited SKILL.md ([README](../README.md) Limits).

The split was swapped before any run. At first the request pair was held out, but that
pair is the only one to use the skill's "When the request carries the claim" section, so
it could not detect overfitting of the rules training tunes. The library-default line in
`SKILL.md` also used to name a rounding mode as its first example, which is
`helper-docstring-lies`' mechanism; that example is gone.

## Checks

Each grader file has `type`, `focus` and `weight`. `weight` is 2 for hidden-test core
checks and for the two core "kept" checks in the docs case, and 1 elsewhere. The harness
counts every check equally; the weight is only for `claude plugin eval`.

- **Core** has two kinds of check, and the benchmark's core column mixes them:
  - Hidden tests, wherever new code is the point: `eval/hidden/<case>/hidden_tests/`, run
    with `gradelib.run_hidden_tests` on a copy of the run. Their grader statements start
    with "Hidden tests pass". They test this skill's distinct claim, that the new code is
    built on what the code really does.
    - Cents pair: the fee's value and type on Decimal or integer totals.
    - Rounding pair: half-up totals, 0.125 -> 0.13 and 4.005 -> 4.01.
    - Request pair: `python -m deliveries.cli` run as a subprocess. The mistyped dates
      2026-13-45 and 31/02/2026, words and blank text exit 2 with "invalid date" on stderr
      and no traceback; valid ISO and day-first dates still print.
  - Text checks on corrections and kept rules: `stale-cents-comment` 02,
    `helper-docstring-lies` 02, `request-quotes-stale-docstring` 02, and all three core
    checks of `docs-sync-keeps-requirements`. Correcting a false description is also what
    the shipped skill asks for, so a tie between `with_skill` and `shipped_skill` is most
    likely here. Read these rows apart from the hidden-test rows in the benchmark's
    per-check table.

  The docs case has no new code. Its core checks are text checks: the stale descriptions
  are fixed, the vendor quota is kept word for word, and the privacy rule survives. The
  privacy rule passes if its sentence is kept word for word, or if a sentence still says
  that section 4 of the privacy policy requires deleted accounts to be left out (a
  requirement word and the exclusion both present). A re-wrapped line, a note added after
  the original sentence, or a final full stop turned into a semicolon still counts as kept.
- **Preservation and restraint** use AST and byte identity:
  - code in the modules the claim is about is unchanged (comments and docstrings aside).
    In the stale request case only `parse_date` and the other original statements of
    `deliveries/dates.py` are compared, so a new function beside `parse_date` passes;
  - files that hold a true claim are byte-identical;
  - the original tests are unchanged (new tests may be added);
  - `round_cents` still rounds half-even, checked by running it after `invoices.total`
    has been imported and called, so a global decimal-context change is caught. A new
    argument whose default keeps half-even passes;
  - no stray files, in every case with new code. The cents pair allows only
    `orders/fees.py` and `tests/`. The other four allow `tests/` and new modules inside
    the existing packages, so a probe script left at the root fails;
  - the true cents fee has no conversion and no guard: no Decimal, float literal, scaling
    by 100, `int()`, `float()` or `round()`, and no condition, type check, raise or assert;
  - the true rounding twin calls `round_cents` (import aliases resolved) and does no
    rounding of its own: no `quantize`, `rounding=`, rounding mode or decimal context;
  - no needless handler (request twin);
  - in the docs case, no line calls the kept privacy rule or quota outdated, obsolete or
    no longer in force, or says deleted accounts may now be exported.
- **Reply** checks read `RESPONSE.md` by keyword. Each case has at least one core check,
  so a reply check never carries a case on its own.
  - Positive reply checks look for the specific correction: the cents comment named with
    a false word, "not cents", "doesn't match", dollars, the tests or a $30 fee; for
    rounding, "even", "not half up" or 0.125 -> 0.12; for the request, "raises" or
    ValueError. In the cents check, the sentence right after the one that names the
    comment may carry the falsity instead, but only in conflict words ("The code and tests
    don't match that.", "That is wrong."), so "Adding 0.30 would be wrong" after a quoted
    comment does not count.
  - The stale request's docstring check (02) fails a sentence that ties None to invalid,
    mistyped or non-existent dates, unless the docstring also says, unnegated, that
    `parse_date` raises. So "None if it is not a date at all; a date that does not exist
    raises ValueError" passes, and "None if text is not a valid date. Never raises." fails.
  - Negative reply checks (the twins) flag a sentence only when a comment, docstring,
    claim, note or doc is what the false word is about: "the docstring is misleading", "a
    stale comment", "the tests contradict the comment". A false word about something else
    ("adding Decimal would be wrong"), a negation within three words before it ("is not
    wrong", "no stale comments") and a hedged clause ("I checked whether the comment was
    stale") do not count. This matters because the skill tells the agent to say a claim
    checked out.

Correcting a false description is graded as core. It is behaviour the coordinator's
direction asks for, and the shipped skill asks for it too ("Treat existing comments as
claims"). That overlap is expected: the `shipped_skill` arm decides whether this skill
adds anything.

## Verified before handing over

- `python incubator/harness.py self-test verify-before-relying` prints `self-test ok`.
  Every reference passes every check, and every unchanged `files/` fails at least one.
- `python incubator/harness.py lint verify-before-relying` prints `lint ok`.
- Each fixture's own unittest suite passes on `files/` and on the reference.
- Simulated outcomes were graded with scratch scripts, outside the repository. The
  review's 47 scenarios, plus 16 new ones and 15 single sentences for the false-alarm
  classifier, now grade as intended, with one deliberate exception: a run that adds a type
  annotation to `Order.total` fails preservation, because that is a code change.
  - Each trap fails its core check:
    - `+ 30` on Decimal totals, including a "reinforced" comment ("in integer cents, not
      dollars");
    - `round_cents` used as asked, and a docstring that restates the false claim as
      "away from zero";
    - a literal doc sync, a deleted requirement, and a requirement stripped of its source;
    - a None-only check on the stale request, and a docstring saying None for "blank or
      invalid" text. After the hardening, the None-only CLI passes words and blanks and
      fails only the two mistyped dates.
  - Each paranoid twin fails a restraint or core check:
    - Decimal fee, type guard or other condition on integer totals;
    - hand-rolled rounding, rounding before `round_cents`, or `round_cents` under a
      half-up local context;
    - a dead `except ValueError`;
    - a reply calling a true comment or docstring misleading or outdated, even when the
      sentence also holds "doesn't" or "nothing".
  - "Fix the code to match the text" fails preservation: `round_cents` rewritten to
    half-up, `parse_date` or `read_date` made to return None (this also breaks
    `tests/test_importer.py`), or tests converted to cents.
  - Probe files left at the repository root fail the stray-files check.
  - A kept rule labelled "(Outdated: ...)" fails the void-label check.
  - Alternative good answers pass:
    - the false comment deleted rather than reworded;
    - a new `round_cents_half_up` helper, a new module in `money/`, a rounding argument
      whose default keeps half-even, or `round_cents` under a local context;
    - a None-returning sibling of `parse_date`, and docstrings that say None "if there is
      no text" or put the raise in a second clause;
    - a reworded page-size line, "10s" or "`GEOCODE_TIMEOUT_SECONDS` (10) seconds";
    - the privacy sentence split into the requirement and a description of the export,
      a note appended after it, and the quota kept with "; the portal sends 250";
    - twin replies that say "I checked whether the comment was stale" or "Decimal would
      be wrong here".
- After the gate, the hardened request pair and the two changed checks were re-verified
  the same way, with 6 + 5 simulated runs, 11 docstring variants and 9 reply variants
  ([GATE.md](GATE.md)). The unchanged cases' gate runs were re-graded in memory with the
  new `grade.py`. Only the misgraded reply changed.
- No 8-word run in these cases, references or hidden tests appears in any `SKILL.md` in
  the repository. `scripts/lint_skills.py` scans `incubator/*/eval/hidden` too, so the
  skill author must not copy hidden-test text either.

## Headroom: what to expect without the skill

- **False-claim cases should show headroom, but how much is uncertain.**
  - `stale-cents-comment`: the main evidence is in a test file, so an agent that never
    opens `tests/test_discounts.py` misses it. The `/ 100` in `apply_discount` is a weak
    second hint. In the gate, Sonnet trusted the comment and added `30`, failing the hidden
    tests. Both Haiku runs read the tests, built on Decimal dollars, and left the comment
    false. So the fixture stays as it is.
  - `request-quotes-stale-docstring`: in the gate, every bare run built the CLI correctly
    (hidden tests 3/3), because `parse_any` had an explicit `raise` and the test name
    `test_text_that_is_not_a_date_raises` said so. The hardened fixture removes both. The
    raise is now implicit in `datetime.date(...)` one file away. The false half covers only
    mistyped dates that have a date's shape, and the visible date tests pin only the true
    half. The evidence is in the importer, its docstring and its test, and in a run of the
    CLI on a typo. Whether bare models now miss it is a hypothesis until the gate is re-run
    ([GATE.md](GATE.md)).
  - `docs-sync-keeps-requirements`: the hygiene eval's reminder arm deleted a true
    free-tier quota in 3 of 5 iteration-5 runs (Haiku runs 1 and 3, Sonnet run 2;
    checked in `evaluation/hygiene/iterations/iteration-5-*/change-contradicts-comment/reminder/`),
    so a "match the code" pull is real. The privacy rule is written descriptively ("are
    left out ... as ... requires") so that a literal sync can flip it. This eval's
    reminder states the requirement rule outright, so the reminder may tie here.
  - `helper-docstring-lies` (held out): the mode is the decimal default, so nothing in
    the function's body says HALF_EVEN. An agent needs the pinned test, a probe, or
    knowledge of the default. In the gate, all three bare runs rounded half up correctly
    (hidden tests 3/3). Its headroom was only in the docstring check (Haiku 0/2). It was
    left as it is ([GATE.md](GATE.md) gives the reason and an option).
- **The twins are guards and should sit at ceiling without the skill.** A bare model
  trusts the claim and passes. They exist to show harm the skill causes, which the round-1
  tournament saw when Haiku with a skill rewrote valid comments. In the gate, every
  complete twin run passed every check.
- `bug-fix-doc-is-right` from the ideation record was dropped. Two of the three judges
  expected it at ceiling, because the bug report already says the code is wrong.

## Design choices to know when reading results

- **No instruction-file cases.** Eval subagents inherit the real worktree's `AGENTS.md`,
  which confounds any fixture `AGENTS.md`, and instruction files are not the user's layer.
- **No "Input files:" line in the requests.** The hygiene prompts list the input files.
  These requests read as a user would write them, so the agent has to find the test or
  helper that holds the evidence itself. All the evidence is inside the repository.
- **`max_turns: 25`** (hygiene used 20), to leave room for reading tests or running a
  probe in every arm.
- **Stopping to ask is a core failure in `helper-docstring-lies`.** The requirement (half
  up, from the tax office) is unambiguous, and only the means the user suggested is
  wrong. The case expects the agent to meet the requirement and report, not to stop.
  Rule otherwise with an override if a run's question is clearly better.
- **In `docs-sync-keeps-requirements` the user said "Don't change any code"**, so the
  privacy bug is reported, not fixed. A run that fixes `export_accounts` fails
  preservation.
- **The privacy sentence mixes a description with a requirement.** `SKILL.md` says such a
  sentence counts as a requirement and is kept as written. The grader also passes a run
  that splits it into the requirement and a description of what the export does, since
  that keeps the rule and its source.
- **Reminder arm** (`arms.json`): one sentence with the full gist, which is check the
  claim, follow the code, correct descriptions, keep requirements and outside facts, and
  report. It includes the requirement rule, so it is not the "follow the code" sentence
  that the docs case would punish. If it ties the skill, the honest recommendation is the
  sentence.
- **Count noticed-but-followed runs by hand**: a reply check that passes while the hidden
  test fails. The benchmark does not separate them.

## Reserve cases (not built)

From the ideation record:
- `outside-fact-vs-constant`: a carrier's batch limit of 100 stated above `MAX_BATCH = 250`,
  when the user asks to batch with `MAX_BATCH`.
- `stale-helper-in-conventions`: a doc names a removed helper; the trap recreates it.

A further held-out pair on a trained channel with a different library default was
suggested in review, for example `csv.writer`'s default `"\r\n"` line ending against a
docstring that says `"\n"`, or a naive `datetime.now()` against a docstring that says UTC.

Each needs a true twin before it is added, to keep the balance.
