# verify-before-relying: results

**The skill ties the one-line reminder on every graded check, on both models, in training
and on the held-out cases.** It beat the shipped `code-comments` skill on Haiku's training
cases (96/96 against 90/96), mostly in one case. That lead did not show on Sonnet or on
the held-out pair, where the shipped skill also scored 100%. Every arm with any guidance
beat the bare model, and only on text checks. No arm's new code was better than the bare
model's on the hidden tests, in any case.

These are small samples: 2 or 3 runs per cell, seven small Python cases, one model family.
The reasoning behind each number is in [ANALYSIS.md](ANALYSIS.md), and the skill edits in
[CHANGES.md](CHANGES.md).

## What ran

Four arms, as the [incubator README](../../README.md) defines them:
- `with_skill` reads this skill's `SKILL.md` snapshot first.
- `shipped_skill` reads a snapshot of the shipped `code-comments` skill first.
- `reminder` gets the one sentence in [arms.json](arms.json) added to the request.
- `without_skill` gets the request alone.

Two models: Claude Haiku and Claude Sonnet. Haiku ran 3 runs per case per arm, Sonnet 2.

| Iteration | Skill | Cases | Arms | Runs |
| --- | --- | --- | --- | --- |
| `gate-haiku`, `gate-sonnet` | none | all 7 | `without_skill` | 21, used for case selection only, not counted ([GATE.md](GATE.md)) |
| `iteration-1-haiku` | v1 | 5 training | all 4 | 60 |
| `iteration-1-sonnet` | v1 | 5 training | all 4 | 40 |
| `iteration-2-haiku` | v2 | 5 training | `with_skill` only | 15 |
| `iteration-2-sonnet` | v2 | 5 training | `with_skill` only | 10 |
| `heldout-haiku` | v2 | 2 held out | all 4 | 24 |
| `heldout-sonnet` | v2 | 2 held out | all 4 | 16 |

165 graded runs are counted. Each iteration's snapshot of `SKILL.md` is kept in its
`skill-snapshot/` folder. The iteration-1 snapshot is v1; the iteration-2 and held-out
snapshots match the current v2. v2 changed only how the reply locates a claim and when it
uses the word "premise" ([CHANGES.md](CHANGES.md)). Iteration 2 re-ran only `with_skill`,
so v2 is compared with the other arms' iteration-1 runs. Those arms do not read this
skill, so the skill edit does not change them.

## Headline (after rulings)

From `python incubator/harness.py summary verify-before-relying iteration-1-haiku
iteration-1-sonnet iteration-2-haiku iteration-2-sonnet heldout-haiku heldout-sonnet`:

| Iteration | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `iteration-1-haiku` | 100.0%, 96/96 | 93.9%, 90/96 | 100.0%, 96/96 | 86.7%, 82/96 |
| `iteration-1-sonnet` | 100.0%, 64/64 | 100.0%, 64/64 | 100.0%, 64/64 | 95.4%, 61/64 |
| `iteration-2-haiku` | 100.0%, 96/96 | not run | not run | not run |
| `iteration-2-sonnet` | 100.0%, 64/64 | not run | not run | not run |
| `heldout-haiku` | 100.0%, 36/36 | 100.0%, 36/36 | 100.0%, 36/36 | 97.2%, 35/36 |
| `heldout-sonnet` | 100.0%, 24/24 | 100.0%, 24/24 | 100.0%, 24/24 | 91.7%, 22/24 |

Pass rate is the mean of each run's share of checks passed. Every run in every arm wrote a
reply (the benchmark's "No reply" column is 0 throughout).

## By focus

Checks passed, summed over runs. Core is split into hidden behavioural tests on the new
code and text checks (corrected descriptions, kept requirements). The hidden tests carry
the question this skill was built for: does the new code rest on what really runs?

| Iteration | Arm | Hidden tests | Core text | Preservation | Restraint | Reply |
| --- | --- | --- | --- | --- | --- | --- |
| `iteration-1-haiku` | with_skill | 12/12 | 15/15 | 30/30 | 21/21 | 18/18 |
| | shipped_skill | **9/12** | 13/15 | 29/30 | 21/21 | 18/18 |
| | reminder | 12/12 | 15/15 | 30/30 | 21/21 | 18/18 |
| | without_skill | 12/12 | **3/15** | 29/30 | 21/21 | 17/18 |
| `iteration-1-sonnet` | with_skill | 8/8 | 10/10 | 20/20 | 14/14 | 12/12 |
| | shipped_skill | 8/8 | 10/10 | 20/20 | 14/14 | 12/12 |
| | reminder | 8/8 | 10/10 | 20/20 | 14/14 | 12/12 |
| | without_skill | 8/8 | 7/10 | 20/20 | 14/14 | 12/12 |
| `iteration-2-haiku` | with_skill | 12/12 | 15/15 | 30/30 | 21/21 | 18/18 |
| `iteration-2-sonnet` | with_skill | 8/8 | 10/10 | 20/20 | 14/14 | 12/12 |
| `heldout-haiku` | with_skill | 6/6 | 3/3 | 12/12 | 9/9 | 6/6 |
| | shipped_skill | 6/6 | 3/3 | 12/12 | 9/9 | 6/6 |
| | reminder | 6/6 | 3/3 | 12/12 | 9/9 | 6/6 |
| | without_skill | 6/6 | 2/3 | 12/12 | 9/9 | 6/6 |
| `heldout-sonnet` | with_skill | 4/4 | 2/2 | 8/8 | 6/6 | 4/4 |
| | shipped_skill | 4/4 | 2/2 | 8/8 | 6/6 | 4/4 |
| | reminder | 4/4 | 2/2 | 8/8 | 6/6 | 4/4 |
| | without_skill | 4/4 | 0/2 | 8/8 | 6/6 | 4/4 |

The hidden tests separate two arms only once: the shipped skill on Haiku in
`request-quotes-stale-docstring`. The bare model passed every hidden test in every case.

## Per case

Checks passed per run, from each iteration's `benchmark.md`. Every run of
`request-quotes-true-docstring`, `true-cents-comment` and `helper-docstring-true` passed
every check in every arm, so those rows are left out.

`iteration-1-haiku`:

| Case | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `docs-sync-keeps-requirements` | 8/8, 8/8, 8/8 | 7/8, 7/8, 8/8 | 8/8, 8/8, 8/8 | 4/8, 6/8, 6/8 |
| `request-quotes-stale-docstring` | 6/6, 6/6, 6/6 | 5/6, 5/6, 5/6 | 6/6, 6/6, 6/6 | 5/6, 5/6, 5/6 |
| `stale-cents-comment` | 6/6, 6/6, 6/6 | 6/6, 5/6, 6/6 | 6/6, 6/6, 6/6 | 5/6, 5/6, 5/6 |

`iteration-1-sonnet`:

| Case | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `docs-sync-keeps-requirements` | 8/8, 8/8 | 8/8, 8/8 | 8/8, 8/8 | 8/8, 7/8 |
| `request-quotes-stale-docstring` | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 |
| `stale-cents-comment` | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 | 5/6, 5/6 |

`iteration-2-haiku` and `iteration-2-sonnet`: every `with_skill` run passed every check in
every case.

`heldout-haiku` and `heldout-sonnet`:

| Case | Model | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- | --- |
| `helper-docstring-lies` | Haiku | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 | 6/6, 6/6, 5/6 |
| `helper-docstring-lies` | Sonnet | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 | 5/6, 5/6 |

### The checks that separated arms

Runs passing, Haiku and Sonnet together (5 runs per arm in each case). Every check not
listed passed in every run of every arm.

| Case: check | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| docs-sync 02, privacy rule kept (core) | 5/5 | 4/5 | 5/5 | 2/5 (Haiku 0/3) |
| docs-sync 03, vendor quota kept word for word (core) | 5/5 | 5/5 | 5/5 | 1/5 (Haiku 0/3) |
| docs-sync 05, true lines unchanged (preservation) | 5/5 | 4/5 | 5/5 | 4/5 |
| docs-sync 08, reply flags the quota (reply) | 5/5 | 5/5 | 5/5 | 4/5 (by ruling) |
| request-stale 01, hidden tests (core) | 5/5 | 2/5 (Haiku 0/3) | 5/5 | 5/5 |
| request-stale 02, docstring corrected (core) | 5/5 | 5/5 | 5/5 | 2/5 (Haiku 0/3) |
| stale-cents 02, cents comment corrected (core) | 5/5 | 4/5 | 5/5 | 0/5 |
| helper-lies 02, docstring corrected (core, held out) | 5/5 | 5/5 | 5/5 | 2/5 (Sonnet 0/2) |

The `with_skill` iteration-2 runs matched their iteration-1 runs on every one of these
checks.

## Held-out cases: does the skill generalise?

The held-out pair is the main test of whether rules tuned on the training cases carry over
to new material. No skill edit looked at it, and it ran once, on v2, after the last edit.

| Check | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| helper-lies 01, hidden tests: totals round half up | 5/5 | 5/5 | 5/5 | 5/5 |
| helper-lies 02, `round_cents` docstring corrected | 5/5 | 5/5 | 5/5 | 2/5 |
| helper-lies 03-06, helper kept, tests, no stray files, reply | 5/5 each | 5/5 each | 5/5 each | 5/5 each |
| helper-true, all six checks (no own rounding, helper untouched, no false alarm) | 5/5 each | 5/5 each | 5/5 each | 5/5 each |

What this shows:
- **The skill held up on new material.** v2 scored 100% on both held-out cases on both
  models. It did not over-distrust the true twin: no run rounded on its own, changed the
  helper or raised a false alarm.
- **It shows no advantage to carry over.** The shipped skill and the reminder also scored
  100%. Every arm, the bare model included, built a correct half-up total (hidden tests
  20/20 across arms). The bare model's only shortfall was leaving the false docstring in
  place (3 of 5 runs). Each of those replies called the docstring wrong but left the fix to
  the user.
- So the held-out result is a tie with both competitors. With 5 runs against 5, 5/5
  against 2/5 has a two-sided Fisher exact p of 0.17, so even the gain over the bare model
  is not established by this pair alone.

## Rulings (overrides) by arm

An auditor agent, not a human, read every failed check and the passing results of every
heuristic check. It wrote seven rulings, all on reply keyword checks. Each is in the run's
`overrides.json`, and the check's own result stays in its `grading.json` evidence.

| Arm | Rulings | Runs |
| --- | --- | --- |
| with_skill | 4, all fail to pass | `iteration-1-haiku`: `stale-cents-comment` run-3 (06), `true-cents-comment` run-2 (06). `iteration-2-haiku`: `stale-cents-comment` run-1 and run-3 (06) |
| shipped_skill | 1, fail to pass | `iteration-1-sonnet`: `stale-cents-comment` run-2 (06) |
| reminder | 1, fail to pass | `iteration-1-haiku`: `stale-cents-comment` run-3 (06) |
| without_skill | 1, pass to fail | `iteration-1-haiku`: `docs-sync-keeps-requirements` run-1 (08) |
| any arm, held out | 0 | |

The rulings favour `with_skill` most, so here are the scores before them:
- `iteration-1-haiku`: with_skill 94/96 (97.8%, reply 16/18), shipped_skill 90/96 (no
  ruling), reminder 95/96 (98.9%), without_skill 83/96 (87.5%).
- `iteration-1-sonnet`: shipped_skill 63/64 (98.3%). The other arms had no ruling.
- `iteration-2-haiku`: with_skill 94/96 (97.8%, reply 16/18).

Before the rulings, the reminder scored one check above `with_skill` on Haiku's training
cases. The tie depends on the rulings. Each ruled reply plainly says what the check asks,
in a wording the heuristic misses: "say otherwise", "That was a false description", a
false word in the sentence before the quote, or a negation more than three words away. The
auditor found no grader bug and no other misgrade.

## Excluded runs

None. `verify-reads` found a transcript for every skill-arm run in every counted iteration
(iteration 1: 50 of 50; iteration 2: 25 of 25; held out: 20 of 20). Every one read its
`SKILL.md` snapshot before its first edit. No run lacked a reply, and none was re-run. The
`verify-reads` output was checked by the auditor and is not stored in the repository.

The gate's 21 bare runs are not counted. They chose and hardened cases before the full run
([GATE.md](GATE.md)).

## What with_skill did that the others did not

**Against the shipped skill** (graded, Haiku only):
- In `request-quotes-stale-docstring`, it built a CLI that handles the real ValueError
  (hidden tests 3/3). The shipped skill noticed the raise in all three runs, built only the
  None check, and asked permission for the rest (0/3). This is the eval's only
  noticed-but-followed pattern. 3/3 against 0/3 has p = 0.10.
- In the docs sync, it kept the privacy rule and the true lines in all runs. The shipped
  skill deleted the privacy rule once and reworded a true line once.
- It corrected the cents comment 3/3 (shipped 2/3).
- On Sonnet and on the held-out pair, they tie.
- Ungraded: the shipped-skill replies asked the user to confirm the unit in 5 of 5
  `stale-cents-comment` runs; `with_skill` asked in none.

**Against the one-line reminder:** nothing graded. Ungraded differences:
- No bytecode caches: `with_skill` left `__pycache__` in 0 of 60 runs; the reminder in
  19 of 25 training runs and 9 of 10 held-out runs. The skill's probe line says to run
  `python -B`. The stray-file checks skip caches by design, in every arm.
- Shorter replies on average (training: Haiku 191 against 212 words, Sonnet 160 against
  169; held out: 191 against 200 and 138 against 196).

**Against no skill:**
- It corrected false descriptions the bare model left: 15 of 15 runs against 4 of 15
  across the three cases that grade it (`stale-cents-comment`, `request-quotes-stale-docstring`,
  `helper-docstring-lies`).
- In the docs sync it kept the requirement and the vendor fact the bare model deleted
  (privacy 5/5 against 2/5, quota 5/5 against 1/5).
- It did not ask the user to decide what the code had already settled (bare: 4 of 5
  `stale-cents-comment` replies asked).
- The reminder and, in most cells, the shipped skill did all of this too.

## What the others did that with_skill did not

- **No arm beat `with_skill` on a graded check.** Preservation and restraint were full for
  `with_skill` in every iteration (120/120 and 85/85 over its 60 runs).
- **v1 caused false line numbers.** Only `with_skill` replies cited `file:line` (112
  citations in 25 runs, none in the other 75). Five pointed past the end of the file, in 3
  runs. v2 dropped the demand: iteration 2 and held out have 0 citations.
- **It misplaced "premise".** Only `with_skill` called a comment's claim "the premise",
  when the request made no claim: 5 of 10 runs of the two cents cases in iteration 1, 2 of
  10 after v2 (Haiku `stale-cents-comment` run-1 and run-2). On the held-out lies case all
  5 `with_skill` replies open "The premise is wrong". That request implies, but does not
  state, that `round_cents` rounds half up, so whether this is a misuse is a judgement.
- **Longer replies than the bare model and the shipped skill** (training v1: Haiku 191
  against 160 and 156 words; Sonnet 160 against 139 and 157).

## Where the numbers come from

- `iterations/<name>/benchmark.json` and `benchmark.md`: every pass rate, focus count, per
  case and per check.
- `iterations/<name>/<case>/<arm>/run-K/`: `grading.json`, `changes.diff`, `RESPONSE.md`,
  and `overrides.json` where a ruling exists.
- Reply length, caches, line citations and "premise" counts were counted from each run's
  `outputs/` by the writer of this file. They are not graded and not in the benchmark.
