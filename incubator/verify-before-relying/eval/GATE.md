# verify-before-relying: gate results and what changed

The gate ran the `without_skill` arm on all seven cases, training and held out: Haiku
twice (`iterations/gate-haiku`) and Sonnet once (`iterations/gate-sonnet`). It asks
whether a bare model already does the right thing, which would leave a case no room to
show a gain. Gate runs are used for case selection only, and they will not be reused as
evaluation runs.

The request pair ran on the fixture as it was before the hardening below. Each of its
runs' `outputs/` and `changes.diff` still shows what that run saw. The gate's
`grading.json` and `benchmark.md` files were not re-graded. They keep the results as
run, and the rulings live here.

## Results per case

Checks passed per run. "Core every run" means every core check passed in all three runs.

| Case | Split | Haiku | Sonnet | Core every run | What the runs did |
| --- | --- | --- | --- | --- | --- |
| `docs-sync-keeps-requirements` | training | 6/8, 6/8 | 7/8 | no | All three deleted Mapline's free-tier quota, saying nothing in the repository supports it. Both Haiku runs rewrote the privacy sentence into a description of the export ("including deleted accounts"); Sonnet kept it. All three replies reported both conflicts |
| `helper-docstring-lies` | held out | 5/6, 5/6 | 6/6 | no | All three met the half-up rule without `round_cents` and left it half-even (hidden tests 3/3). Both Haiku runs said the docstring was wrong, left it, and asked the user to decide. Sonnet corrected it |
| `helper-docstring-true` | held out | 6/6, 6/6 | 6/6 | **yes** | All three checked `round_cents`, trusted it and used it |
| `request-quotes-stale-docstring` | training | 5/6, 5/6 | 5/6 | no | All three found the raise (an explicit `raise` in `parse_any`, and a test named `test_text_that_is_not_a_date_raises`). All three caught ValueError in the CLI (hidden tests 3/3) and told the user. None corrected the docstring; all three offered to |
| `request-quotes-true-docstring` | training | 6/6, 6/6 | 6/6 | **yes** | A None check only, and no false alarm |
| `stale-cents-comment` | training | 4/6 (5/6 after the fix), 5/6 | 3/6 | no | Sonnet trusted the comment and added `30` (hidden tests fail); its reply cites only the comment and says it did not run anything. Both Haiku runs built on Decimal dollars from the tests, left the comment false and reported the conflict |
| `true-cents-comment` | training | 6/6, 3/6 | 6/6 | no, but see below | Haiku run 2 did nothing: no `orders/fees.py`, no `RESPONSE.md`, and no file changed. The other two runs passed every check |

## Rulings on every failed check

| Case, check | Runs | Ruling |
| --- | --- | --- |
| docs-sync 02, privacy rule kept | Haiku 1, 2 | Correct failure. The requirement was rewritten as a description of the bug |
| docs-sync 03, vendor quota kept | all three | Correct failure. A vendor fact the code cannot disprove was deleted |
| helper-lies 02, docstring corrected | Haiku 1, 2 | Correct failure. The run knew the docstring was false and left it. The case's expected outcome asks for the correction. Whether a correction nobody asked for is wanted is the open policy question in the skill README (next steps, item 7); it is not a grader error |
| request-stale 02, docstring corrected | all three | Correct failure, for the same reason. Each reply said the docstring was wrong and offered to fix it |
| stale-cents 01, hidden tests | Sonnet | Correct failure: the trap (`+ 30` on Decimal dollar totals) |
| stale-cents 02, comment corrected | all three | Correct failure. Haiku wrote "I did not change the comment in `model.py`, because it is outside this task" |
| stale-cents 06, reply flags the comment | Sonnet | Correct failure. The reply repeats the false claim as fact |
| stale-cents 06, reply flags the comment | Haiku 1 | **Grader bug.** The reply says: 'the comment on `Order.total` in `orders/model.py` says "amount due, in integer cents". The code and tests don't match that.' It then says the comment "should be corrected". Haiku run 2's reply says the same thing ("which contradicts how the tests and the discount code use it") and passed. The check read each sentence on its own, and this reply puts the "don't match" in the sentence after the one that names the comment. Fixed below |
| true-cents 01, 03, 06 | Haiku 2 | Correct failures, but of a run that never worked: it left only the original files and no reply. That says nothing about trust or paranoia, so no check changed. When reading arm results, count such runs apart (the benchmark's "No reply" column) or re-run them |

## Grader fixes

1. **`stale-cents-comment` 06** (`reply_flags_cents_comment`). A sentence that names the
   cents comment now passes in two ways:
   - it also says the comment is false in place, using the existing markers plus a new
     "don't match / doesn't agree" marker;
   - or the next sentence sets something against it in conflict words only:
     "contradicts", "disagrees", "doesn't match", or a sentence opening "That is wrong" or
     "It was stale". A negated conflict word ("The tests don't contradict that.") does not
     count.

   A bare false word in the next sentence also does not count, so "The comment on
   Order.total says integer cents. Adding 0.30 would be wrong." still fails. Re-grading
   every gate run of the unchanged cases in memory changed only this run's 06 (false to
   true). Nine reply variants grade as intended, including Sonnet's reply, which still
   fails.
2. **`request-quotes-stale-docstring` 02** (`parse_date_docstring_corrected`), changed
   with the hardening below, not because of a misgrade. In the new fixture, None for words
   is true and None for mistyped dates is false. So a correct docstring may say "None if it
   is not a date at all" as long as it also says the raise. The check now fails a sentence
   tying None to invalid, mistyped or non-existent dates only when the docstring does not
   also say, unnegated, that `parse_date` raises. "Never raises" and "instead of raising"
   count as negated. Eleven docstring variants grade as intended.

No check was loosened so that a run the gate graded as a failure would now pass, apart
from the one misgraded reply. Every other gate result of the unchanged cases is the same
under the new `grade.py`.

## Ceiling cases

By the rule that every core check passed in all three runs, two cases are at ceiling:
`helper-docstring-true` and `request-quotes-true-docstring`. Both are **deliberate
control cases**. They are true twins whose job is to catch the over-distrust a skill can
cause, so a bare model should pass them. They stay at ceiling. `true-cents-comment` is
the same kind of control and is at ceiling apart from the empty run.
`request-quotes-true-docstring` was still changed, but only to stay the twin of the
hardened case below. It remains a control at ceiling by design.

## Hardening: `request-quotes-stale-docstring`

The core-every-run rule does not flag this case, because the docstring check failed in
all three runs. But its hidden tests passed in all three runs, and those test the
behaviour this skill adds over the shipped one: building on what the code does when the
request repeats a false claim. Two things ask for the remaining docstring correction in
so many words: the reminder sentence ("correct any description of it that is wrong") and
the shipped skill. So as built, the case could show a gain over the bare model, but not
over either competitor on the behaviour the skill is for. In the gate the evidence was too
loud: an explicit `raise ValueError(...)` one call away, and a visible test named
`test_text_that_is_not_a_date_raises`.

What changed (the request text is word for word the same):
- **The false half is narrower and closer to what the user asked about.** Text with no
  date in it (blank, "tbc", "next tuesday") really does return None. A mistyped date that
  still has a date's shape (2026-13-45, 31/02/2026) raises ValueError. The user asked for
  exactly that case: "so a mistyped date gets a clear error message".
- **The raise is implicit and one file away.** `read_date` in `deliveries/formats.py`
  matches a date shape and builds the date with `datetime.date(...)`, which raises for a
  day that does not exist. No `raise` statement says so.
- **The visible date tests pin only the true half.** `tests/test_dates.py` checks that
  blank and "tbc" give None. Reading it confirms the premise, so it is a distractor.
- **The evidence moved to the caller.** `deliveries/importer.py` catches the ValueError,
  and its docstring says such rows are listed so the warehouse can correct the typo.
  `tests/test_importer.py` pins this: a "31/02/2026" row is listed and a "tbc" row is left
  out. That test also makes "fix `read_date` to return None" fail visibly, so changing the
  code to match the docstring is still a preservation failure, not a defensible choice.

The natural wrong edit is a None-only check. It passes the visible tests and a manual run
with "next tuesday" or a blank, and crashes with a traceback on 2026-13-45. The hidden
tests now also cover 31/02/2026. A competent but unaware editor who trusts the request
and the date tests misses it. An editor who checks finds it in any of three places: the
`datetime.date` call, the importer's handler and docstring, or a run of the CLI on a
typo. Whether bare models now miss it is a **hypothesis**. In the gate, Haiku run 2
already tried 2026-13-45 by hand, so some bare runs will still pass. Re-run the gate on
this pair before the other arms.

The twin, `request-quotes-true-docstring`, keeps the same request and the same visible
date tests. Its `read_date` catches the ValueError and returns None, and its docstring
says so. Its importer treats None as a skipped row, and its importer test lists both
"tbc" and "31/02/2026" as skipped.

Verified after the change:
- Both fixtures' own tests pass on `files/` and on the reference.
- The hidden tests fail on `files/` and pass on the reference.
- Simulated runs grade as intended:
  - a None-only CLI fails 01, 02 and 06;
  - the gate's "both paths, docstring left" shape fails only 02;
  - "fix `read_date`" fails 03 and 04;
  - a None-returning sibling beside `parse_date` passes every check;
  - a probe left at the root fails 05;
  - on the twin, a dead handler fails 04, a false alarm fails 06, an edited docstring
    fails 02, and an empty run fails 01.

## Not hardened: `helper-docstring-lies` (held out)

It has the same pattern: hidden tests 3/3, with the headroom only in the docstring
check (Haiku 0/2). It was left as it is for three reasons:
- it is held out, so it should change as little as possible;
- its core text check does show headroom;
- it rests on one library-default fact that the skill README's limits section discusses.

If hidden-test headroom on the held-out pair is wanted, this option keeps the mechanism
and all the evidence. Move the half-even pin out of `tests/test_rounding.py` (the runs
quoted its test name and its bank comment) into a ledger test. Leave
`tests/test_rounding.py` with values that half up and half-even round the same way.

## What the gate suggests for the full run

- **Noticed but not corrected is the main bare-model pattern.** Eight runs noticed a
  false description of the code. Seven of them reported it and left the text false: all
  six Haiku runs, and Sonnet in the request case. Sonnet corrected only the rounding
  docstring.
- **The reminder will probably close the text gaps.** It asks for that correction, and
  for keeping requirements and outside facts, in so many words. So expect it to close much
  of the gap on the text-correction core checks and in the docs case. The `with_skill`
  against `reminder` question then rests mainly on the hidden tests: Sonnet in
  `stale-cents-comment`, and the hardened request case. The gate measured headroom over
  the bare model only.
- The skill README (outside `eval/`) said the gate was a next step when this was written.
  It now records the gate as done and links here. Its row for the request case ("the
  request repeats a half-true docstring") still holds.
