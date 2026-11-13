# code-comments-v5: training and hygiene cases

Every training and hygiene case is a whole copy of a case from another eval: its prompt,
case.yaml, graders, files, reference and hidden tests. `grade.py` grades each one with
its source eval's own checks. This file describes the 10 training cases and the 11 hygiene cases.
It does not describe the held-out cases. Candidate writers read this file, not
[HELD-OUT.md](HELD-OUT.md).

Run figures below are from the source evals' records. They are not results of this
climb. "v4" is the shipped skill (the `shipped_skill` arm there), "bare" is the
`without_skill` arm.

## How the copies are graded

- Checks are taken unchanged from the source `grade.py`. Hidden tests run from the
  source folder, which holds the same files as `hidden/` here.
- Each grader file sets a `focus`. `core` is the target behaviour, graded by hidden tests
  where it can be. `preservation`, `restraint` and `reply` are what must not be damaged,
  what must not be added, and what the reply says.
- The hygiene graders carry no focus the harness reads. The copies drop their
  `focus: trace` line, a `claude plugin eval` field that the harness rejects, so every
  hygiene check counts as core. Their statement text is unchanged.
- The hygiene copies' case.yaml also gains `held_out: false`.
- `tests/test_incubator.py` fails if a copy drifts from its source
  (`grade.py`'s `drift()`).

Checks per run of each case: training 64 in all, 14 of them core; screen 28; hygiene 59.

## Training cases: false premises (FM1)

From `incubator/verify-before-relying`. Each gives the agent a claim that new code would
rely on. In two the claim is false, in two it is true, and in one a doc mixes stale
descriptions with rules the code breaks.

### `request-quotes-stale-docstring`
- **Tests:** the user's request repeats `parse_date`'s docstring: it returns None for
  anything that is not a valid date. That is only half true: a date-shaped typo such as
  31/02/2026 raises ValueError. The CLI must handle both, so every mistyped date gets the clear error the
  user asked for. The docstring is corrected and the reply says the premise was wrong.
- **Why here:** this is FM1. With v4, all three Haiku runs in
  `incubator/verify-before-relying/eval/iterations/iteration-1-haiku/request-quotes-stale-docstring/shipped_skill/`
  corrected the docstring, then built only the None check, and failed the hidden tests
  (0/3). Run 1's reply says "I did not handle that because you asked for the None case
  only." Run 3 says the same, and run 2 offers to add it if asked. The bare model passed
  the hidden tests in 3 of 3 runs (p = 0.10) but left the docstring false.

### `request-quotes-true-docstring`
- **Tests:** the same request, but here the docstring is true. The CLI checks for None
  and adds no handler for an exception `parse_date` never raises. The reply does not
  call the docstring wrong.
- **Why here:** the twin of FM1. It catches a fix that makes the agent distrust every
  quoted claim. v4 passed every check in every run (Haiku 3/3, Sonnet 2/2).

### `stale-cents-comment`
- **Tests:** add a 30-cent fee in a new file. A comment says totals are integer cents,
  but the tests build Decimal dollar totals. The fee must be Decimal("0.30"), the comment
  is corrected, and the reply says it was wrong.
- **Why here:** a false comment with no false premise in the request. A fix for FM1
  must keep v4's correction. v4 left the cents claim in place once (Haiku run 2 in
  `incubator/verify-before-relying/eval/iterations/iteration-1-haiku/stale-cents-comment/shipped_skill/`).
  The bare model missed at least one check in each of its 3 Haiku runs.

### `true-cents-comment`
- **Tests:** the same request, where the cents comment is true. The new code trusts it:
  no Decimal, no division by 100, no guard.
- **Why here:** the twin. It catches over-checking. v4 passed every check in every run.

### `docs-sync-keeps-requirements`
- **Tests:** bring `docs/limits.md` in line with the code without changing code. Two
  stale descriptions are fixed. A vendor quota and a privacy-policy rule, which the code
  breaks, stay as written, are not labelled void, and both conflicts are reported.
- **Why here:** the training case closest to the counter-guard. It tests the good side
  of the conflict rule (keep an outside fact and report it). A change to that rule must
  not lose it. v4 passed 22 of 24 Haiku checks. Haiku run 2 failed the check that the
  privacy rule is still stated
  (`incubator/verify-before-relying/eval/iterations/iteration-1-haiku/docs-sync-keeps-requirements/shipped_skill/run-2/`).
  The bare model passed 16 of 24.

## Training cases: constraints held elsewhere (FM2)

From `incubator/constraint-sweep`. Each change touches something that another file
relies on, says relies on, or reaches by name. The hidden tests check that the other
file still works.

### `positional-columns-in-sql`
- **Tests:** add a currency column next to amount. The user says column order is free,
  and every Python reader agrees. But a warehouse SQL load reads the CSV by position,
  and its comment says new columns go at the end. Preferred: put currency next to
  amount and change the SQL in step. Accepted: put it at the end and say why.
- **Why here:** FM2. With v4, Haiku runs 2 and 3 in
  `incubator/constraint-sweep/eval/iterations/iteration-1-haiku/positional-columns-in-sql/shipped_skill/`
  found the SQL comment, put currency next to amount, left the SQL alone and failed the
  hidden tests. Run 2's reply says "this change breaks it" and "I did not touch the
  deploy files because you did not ask for that." Run 3 left the SQL for "an owner's
  decision".

### `positional-columns-in-sql-pointer`
- **Tests:** the same case, plus a pointer comment above `COLUMNS` in the file being
  edited that names the SQL file.
- **Why here:** FM2 with the evidence at the point of edit. v4 Haiku run 2 in
  `incubator/constraint-sweep/eval/iterations/iteration-1-haiku/positional-columns-in-sql-pointer/shipped_skill/`
  still broke the load: "I did not change the SQL, because it is outside the request."
  Every v4 run that broke the load named the SQL file in its reply, so finding the
  constraint was not what failed.

### `sort-relied-on-elsewhere`
- **Tests:** drop a slow Python sort. The user says neither Python caller needs the
  order, and that is true. But a shell script uploads the export to a bank that rejects
  it unless ids ascend. The rows must still come back in id order, for example by
  ORDER BY in the query, and the reply names the upload.
- **Why here:** FM2. v4 broke the upload and said so in Haiku runs 1 and 3
  (`incubator/constraint-sweep/eval/iterations/iteration-1-haiku/sort-relied-on-elsewhere/shipped_skill/`)
  and Sonnet run 1
  (`incubator/constraint-sweep/eval/iterations/iteration-1-sonnet/sort-relied-on-elsewhere/shipped_skill/run-1/`).
  Haiku run 1's reply says "I did not move the sort into the export, because you asked
  only to drop it."

### `stale-constraint-elsewhere`
- **Tests:** take a sort out. A comment elsewhere says a consumer relies on the order,
  but that consumer sorts its own input, so the claim is stale. The change goes ahead,
  no sort moves into a consumer, and the stale claim is corrected or reported.
- **Why here:** the guard against over-correction. A fix that makes the agent obey
  every stated constraint fails here. v4 passed every check in every run.

### `dispatched-by-name`
- **Tests:** remove dead code. Two functions really are dead. A third looks dead but is
  reached by a name built at runtime from a config file, so it must stay, and the reply
  says why.
- **Why here:** a constraint found only by reading how code is reached. Keeping every
  handler also fails, so it guards restraint too. v4 passed every check in every run.

## Hygiene cases (regression)

From `evaluation/hygiene`. These are the cases v4 was built on. The five marked
**screen** run in every round. All 11 run in the final validation. Iteration-5 figures
are from `evaluation/hygiene/iterations/iteration-5-haiku/` and `iteration-5-sonnet/`
(v4 is "Skill v4" there).

### `change-contradicts-comment` (screen)
- **Tests:** the user asks to raise a request limit to 250 a minute. A comment says the
  vendor's free tier allows 100. The limit becomes 250, the quota fact stays as written,
  no comment claims 250 is allowed, and the reply flags the conflict.
- **Why here:** the counter-guard. Here the user asks for the change outright, and v4 is
  right to make it and report. v4 passed every check in every iteration-5 run (Haiku
  3/3, Sonnet 2/2). Three reminder runs deleted the quota. A fix for FM2 must keep this:
  the line runs between a change the user asked for and breakage the request did not
  knowingly ask for.

### `no-invented-reason` (screen)
- **Tests:** change a timeout from 30 to 15 minutes, with no reason given. No comment
  invents one, and the reply says the reason is missing or asks for it.
- **Why here:** it rewards the report-and-ask habit that hypothesis (b) blames for FM1.
  In iteration 5 every v4 run told the user no reason was given, and no reminder or
  bare run did (v4 5/5 in every run on both models, every other run 4/5). A fix that
  weakens "ask for it" may lose this.

### `issue-pointer-beside-reason` (screen)
- **Tests:** format amounts with two decimals for a vendor's importer, from issue #212.
  A short comment gives the vendor's reason and cites #212 after it.
- **Why here:** v4's largest lead on Haiku in iteration 5 (5/6, 6/6, 4/6 against 3/6 in
  every reminder run). It also has a comment-length limit, which a longer skill may push
  past.

### `reason-only-in-test` (screen)
- **Tests:** simplify a function. Its old shape hid a rule (the last update wins), which
  only a test explains. The rule and its reason are stated beside the new code.
- **Why here:** it discriminated in iteration 5 (Haiku v4 4/6, 6/6, 6/6) and tests the
  "a rule that a rewrite hides" bullet, which a candidate edit may move or shorten.

### `capture-supported-reason` (screen)
- **Tests:** sort a batch for a loader in another repository, from a ticket. A short
  comment records why the sort is needed, and no ticket id is invented.
- **Why here:** the case where v4 lost in iteration 5: both Sonnet runs added more than
  four comment lines (4/5 each). It watches comment length, where added skill text may
  add noise.

### `clause-goes-stale`
- **Tests:** `parse_tags` returns [] for None but still raises for text with no tags.
  The docstring clause about None is fixed, the rest kept, and a caller's comment
  corrected.
- **Why here:** regression guard. Every arm passed every check in iteration 5.

### `comment-only-preserve`
- **Tests:** a comment-only review. False claims are fixed, no code changes, and the
  licence header, tool directive and accurate comments stay word for word.
- **Why here:** regression guard for the comment-only section. No arm differed in
  iteration 5.

### `no-issue-tag-routine`
- **Tests:** add a `--limit` option for issue #318. No comment or help text tags the
  code with #318.
- **Why here:** regression guard for "do not tag code with the issue". No arm differed in
  iteration 5.

### `rename-stale-refs`
- **Tests:** rename a function across a package. Every comment, docstring and doc that
  named it is updated, and the explanations around the name survive.
- **Why here:** regression guard. No arm differed in iteration 5.

### `retry-cap-elsewhere`
- **Tests:** raise retries from three to five. Every comment, docstring and doc that
  described three retries is corrected, including ones far from the constant.
- **Why here:** it tests "update every statement of what this code does", the last
  sentence of the conflict rule that a candidate edit is likely to touch. On Sonnet in
  iteration 5, v4 passed 5/5 in both runs and the bare model 4/5 once.

### `routine-edit-no-noise`
- **Tests:** add a `--quiet` option. At most one comment line is added and existing
  comments are unchanged.
- **Why here:** regression guard for restraint. No arm differed in iteration 5.
