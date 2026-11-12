# code-comments-v5 results

Date: 2026-11-11. The climb followed the method and the rules in [README.md](README.md),
which were committed before any run.

## Outcome: null

All three round-1 candidates were rejected by the screen rule. A round that improves
nothing stops the climb, so the climb stopped after round 1. No candidate beat v4. The
result is null: the final validation was not run, and the shipped skill does not change.

The training gain was large. Each candidate passed 41 or 42 of the 42 training core
checks, against v4's 30. Every candidate lost 2 to 3 screen checks. The rule allows a
loss of 1.

## Round 0, the baseline (Haiku)

| arm | train core | train all | train non-core | screen all |
| --- | --- | --- | --- | --- |
| v4 (`shipped_skill`) | 30/42 | 173/192 | 143 | 55/56 |
| bare (`without_skill`) | 29/42 | 171/192 | 142 | not run |

## Round 1 (Haiku, 3 training runs and 2 screen runs per candidate)

- r1-a edits rule (a), the conflict rule, only.
- r1-b edits habit (b), the report-and-ask lines, only.
- r1-c edits both.

| candidate | train core | train all | train non-core | screen all | ask-first runs | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| r1-a | 42/42 | 183/192 | 141 | 53/56 | 0 | rejected: screen 2 below v4 |
| r1-b | 41/42 | 182/192 | 141 | 53/56 | 0 | rejected: screen 2 below v4 |
| r1-c | 42/42 | 185/192 | 143 | 52/56 | 0 | rejected: screen 3 below v4 |

The reject thresholds:
- screen below 54 (v4's 55 minus 1);
- training non-core below 140 (v4's 143 minus 3);
- more ask-first runs on `change-contradicts-comment` than v4's 0.

Only the screen rule fired.

Per training case (core passed, all passed; pooled over 3 runs):

| training case | v4 | bare | r1-a | r1-b | r1-c |
| --- | --- | --- | --- | --- | --- |
| request-quotes-stale-docstring | 3/6, 15/18 | 1/6, 13/18 | 6/6, 18/18 | 6/6, 18/18 | 6/6, 18/18 |
| request-quotes-true-docstring | 3/3, 18/18 | 3/3, 18/18 | 3/3, 18/18 | 3/3, 17/18 | 3/3, 17/18 |
| stale-cents-comment | 2/6, 14/18 | 2/6, 14/18 | 6/6, 18/18 | 6/6, 18/18 | 6/6, 18/18 |
| true-cents-comment | 3/3, 18/18 | 3/3, 18/18 | 3/3, 17/18 | 3/3, 18/18 | 3/3, 18/18 |
| docs-sync-keeps-requirements | 7/9, 22/24 | 5/9, 20/24 | 9/9, 24/24 | 8/9, 23/24 | 9/9, 24/24 |
| positional-columns-in-sql | 3/3, 21/21 | 3/3, 21/21 | 3/3, 20/21 | 3/3, 20/21 | 3/3, 21/21 |
| positional-columns-in-sql-pointer | 3/3, 21/21 | 3/3, 19/21 | 3/3, 20/21 | 3/3, 21/21 | 3/3, 21/21 |
| sort-relied-on-elsewhere | 0/3, 11/21 | 3/3, 15/21 | 3/3, 15/21 | 3/3, 15/21 | 3/3, 15/21 |
| stale-constraint-elsewhere | 3/3, 15/15 | 3/3, 15/15 | 3/3, 15/15 | 3/3, 14/15 | 3/3, 15/15 |
| dispatched-by-name | 3/3, 18/18 | 3/3, 18/18 | 3/3, 18/18 | 3/3, 18/18 | 3/3, 18/18 |

Per screen case (all passed; pooled over 2 runs):

| screen case | v4 | r1-a | r1-b | r1-c |
| --- | --- | --- | --- | --- |
| no-invented-reason | 10/10 | 10/10 | 10/10 | 10/10 |
| issue-pointer-beside-reason | 11/12 | 10/12 | 11/12 | 11/12 |
| change-contradicts-comment | 12/12 | 12/12 | 12/12 | 12/12 |
| reason-only-in-test | 12/12 | 11/12 | 11/12 | 11/12 |
| capture-supported-reason | 10/10 | 10/10 | 9/10 | 8/10 |

The screen losses, read from each failing run:
- **capture-supported-reason** (r1-b 1 run, r1-c 2 runs): 5 to 7 comment lines were
  added, where the case allows 4. Each one named the reason and what relies on it at
  length.
- **reason-only-in-test** (every candidate, 1 run): the added comment gave the mechanism
  ("moves the SKU to the end") but not the reason the test records, that later updates
  are corrections.
- **issue-pointer-beside-reason** (r1-a 2 runs, r1-b 1, r1-c 1; v4 1): the run rewrote
  `format_amount`'s docstring, although the docstring was still true.

## Rulings and exclusions

There was 1 ruling, made by the coordinator agent, not a human. It is in
`eval/iterations/round-1-a-haiku/change-contradicts-comment/with_skill/run-2/overrides.json`.
- The heuristic check flagged 2 added lines as saying the quota allows 250 requests a
  minute. Both say the opposite: 250 is above the quota and gets HTTP 429.
- Every other `change-contradicts-comment` run, in round 0 and in all three candidates,
  passed this check, so no other run changed.
- The ruling raised r1-a's screen from 52 to 53. That did not change the verdict.

Rulings per arm:

| arm | rulings |
| --- | --- |
| v4 | 0 |
| r1-a | 1 |
| r1-b | 0 |
| r1-c | 0 |

**Excluded runs:** none.
- **verify-reads:** each candidate iteration checked 40 runs. None skipped the skill, none
  read it only partly, and no transcript was missing.
- **Run-limits guard:** it stopped no graded write.

**Writer exposure scan.** The scan covered every tool call in each candidate writer's
transcript and looked for any file or folder the README forbids, including the 8
held-out case names. It found:

| writer | tool calls naming a forbidden file or folder |
| --- | --- |
| r1-a | 0 |
| r1-b | 0 |
| r1-c | 1 |

The r1-c match is its final structured answer, not a file access: the summary text says
it did not run `self-test` or `test_heldout.py`. No writer opened a held-out file.

## What this suggests (hypotheses, not shown)

- Both edits close the training failure modes. They are FM1, building on a false
  docstring the request quotes, and FM2, breaking a constraint the run had found.
  Either edit alone was enough: r1-a and r1-c reached 42/42, and r1-b 41/42.
- These are the selection runs. G1 would overstate them (README, "Limits known in
  advance"), and nothing here is a held-out result.
- The cost falls on comment economy. The new rules tell the agent to name what relies on
  a constraint and to correct stale claims. On cases where the right edit is a short
  reason, the runs wrote longer comments, rewrote a true docstring, or wrote the mechanism
  instead of the reason.
- A next climb would start from r1-a or r1-c. It would add a line that keeps the new
  reasoning in the reply and the code, and keeps comments to the one reason. It needs its
  own pre-registration. The training cases have now been used for selection once, so
  reusing them adds selection bias; fresh training cases would avoid that.

## Files

- `candidates/r1-a/`, `candidates/r1-b/`, `candidates/r1-c/`: each candidate's SKILL.md.
- `eval/iterations/round-0-haiku/` and `eval/iterations/round-1-{a,b,c}-haiku/`: every
  run's prompt, response, diff and grading.
  - Each round-1 iteration has a `skill-snapshot/` holding the text that ran.
- `skill/code-comments-v5/SKILL.md` is back at v4 renamed, as committed with the method.
