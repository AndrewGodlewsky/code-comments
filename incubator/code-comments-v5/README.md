# code-comments-v5

**Status: pre-registered; not run.**

A hill-climb on the shipped `code-comments` skill
([plugins/code-comments/skills/code-comments/SKILL.md](../../plugins/code-comments/skills/code-comments/SKILL.md),
called v4 here). It starts from a copy of v4,
[skill/code-comments-v5/SKILL.md](skill/code-comments-v5/SKILL.md), which differs only in
its frontmatter name (the linter needs name and folder to match). The description is v4's
word for word, because it governs activation, which this climb must not change.

This file was written before any run. The method, the selection rule and the gates below
do not change once the first run starts. A change made later is recorded as a deviation,
with its date and reason, and the result is reported both ways where it can be.

It was revised on 2026-11-11, still before any run, after a review of the held-out cases
built for this climb. The revision restated the counter-guard line, added two reject
rules to the selection, added a clause each to G1 and G2, and defined the tie-break
length. [eval/HELD-OUT.md](eval/HELD-OUT.md) records which review findings prompted
which change.

## Purpose

The incubator evals of #50 found two ways v4 does worse than the bare model. In both, v4
found the problem, said so, and still built the narrower or breaking change. The climb
asks whether a small edit to v4 removes those failures without losing what v4 does well
on the hygiene cases it was built on.

## The failure evidence

These are measured results from earlier runs, in the records named.

**FM1: noticed a false premise, then followed it.** In
`incubator/verify-before-relying`, case `request-quotes-stale-docstring`, the user's
request repeats `parse_date`'s docstring: it returns None for anything that is not a
valid date. That is only half true: a date-shaped typo really raises ValueError.
- With v4, all three Haiku runs corrected the docstring, then built only the None check:
  `incubator/verify-before-relying/eval/iterations/iteration-1-haiku/request-quotes-stale-docstring/shipped_skill/run-1/`
  to `run-3/`.
- Run 1's reply says: "I did not handle that because you asked for the None case only."
  Run 3 says the same. Run 2 offers to add it if asked.
- Hidden tests passed in 0 of 3 v4 runs and in 3 of 3 bare runs (p = 0.10).

**FM2: found a constraint stated in another file, then broke it.** In
`incubator/constraint-sweep`, v4 did this, and said so, in 6 of 25 iteration-1 runs:
- Haiku `positional-columns-in-sql` runs 2 and 3, Haiku
  `positional-columns-in-sql-pointer` run 2, Haiku `sort-relied-on-elsewhere` runs 1
  and 3, under `incubator/constraint-sweep/eval/iterations/iteration-1-haiku/<case>/shipped_skill/`;
- Sonnet `sort-relied-on-elsewhere` run 1, under
  `incubator/constraint-sweep/eval/iterations/iteration-1-sonnet/`.
- The replies give the request as the reason: "I did not touch the deploy files because
  you did not ask for that", "because it is outside the request", "because you asked only
  to drop it".
- No other arm broke a constraint. Core checks: v4 19/25, every other arm 25/25
  (p = 0.022).

**For orientation**, the 10 training cases scored with `eval/score.py` on the earlier
Haiku iteration-1 records (3 runs each): v4 passed 32 of 42 core checks and 171 of 192
in all; the bare model 30 of 42 and 170 of 192. The climb re-runs both arms rather than
reusing these.

## Hypothesis

This is a hypothesis to test, not a result. Two v4 rules drive both failures:
- **(a) The conflict rule:** "If the requested change breaks a limit or requirement that
  a comment states, make the change if asked and tell the user about the conflict in
  your reply." Haiku reads "make the change if asked" as licence to break a constraint
  the user never knew about, as long as the reply mentions it.
- **(b) The report-and-ask habit:** "Report unverifiable gaps to the user" and "ask for
  it". Haiku reads these as licence to build only the literal ask and hand the rest back.

**The counter-guard.** In the hygiene case `change-contradicts-comment`, the user
explicitly asks to raise a limit past an outside quota that a comment states. v4 rightly
makes the change, keeps the quota as written and reports the conflict. A fix must keep
that. The line runs here: when breaking the stated limit is the requested change itself,
make the change and report the conflict; avoid breakage that the request does not need.
This climb counts asking first, with no change, as wrong on `change-contradicts-comment`,
although that case's first check accepts it (see the selection rule).

**What the hypothesis predicts.** An edit to (a) and (b) that draws that line raises v4's
hidden-test passes on `request-quotes-stale-docstring`, `positional-columns-in-sql`,
`positional-columns-in-sql-pointer` and `sort-relied-on-elsewhere` on Haiku, and keeps
full marks on `change-contradicts-comment`. If an edit to (a) alone fixes FM2 but not
FM1, or the reverse, the hypothesis holds only in part.

## What is here

```text
code-comments-v5/
  README.md              this file
  skill/code-comments-v5/SKILL.md   the candidate under test; starts as v4 renamed
  eval/
    arms.json            the reminder sentence of hygiene iteration 5 (no arm here uses it)
    cases/               29 cases: 25 whole copies (10 training, 11 hygiene, 4 held out)
                         and 4 held-out cases built for this climb
    references/, hidden/ the references and hidden tests
    grade.py             adapter: each copied case keeps its source eval's checks
    heldout_fm1.py, heldout_fm2.py   checks for the held-out cases built for this climb
    test_heldout.py      pinned variants for those checks
    score.py             scores iterations by case group, for the selection rule and gates
    CASES.md             the training and hygiene cases
    HELD-OUT.md          the held-out cases
    iterations/          run records, written by the climb
```

The case groups:
- **train**: the 10 training cases, from `incubator/verify-before-relying` (5) and
  `incubator/constraint-sweep` (5). 64 checks per run of every case, 14 of them core.
- **screen**: five hygiene cases that separated v4 from the other arms in hygiene
  iteration 5: `no-invented-reason`, `issue-pointer-beside-reason`,
  `change-contradicts-comment`, `reason-only-in-test`, `capture-supported-reason`. 28
  checks.
- **hygiene**: all 11 cases from `evaluation/hygiene`, the screen included. 59 checks.
  Every hygiene check counts as core (see [eval/CASES.md](eval/CASES.md)).
- **heldout**: every case whose case.yaml says `held_out: true`, listed in
  [eval/HELD-OUT.md](eval/HELD-OUT.md). There are 8: 4 copied and 4 built for this climb.

## Method

**Arms.** v4 is the harness's `shipped_skill` arm, which reads a snapshot of the plugin's
SKILL.md. A candidate is the `with_skill` arm, which reads a snapshot of
`skill/code-comments-v5/SKILL.md` as it stood at `prepare`. The bare model is
`without_skill`. The reminder arm is not used. `arms.json` exists because the harness
reads it.

**Round 0, the baseline.** v4 and the bare model on the training cases, Haiku, 3 runs
each. v4 on the screen, Haiku, 2 runs.

**Rounds 1 to 3.** Each round writes three candidate edits of the best skill so far
(round 1 edits v4). Each candidate runs on the training cases (Haiku, 3 runs) and the
screen (Haiku, 2 runs). Round 1 tests the hypothesis by parts: one candidate changes
rule (a) only, one changes the habit (b) only, and one changes both.

**Selection.** Candidates are ranked by, in order:
1. training core checks passed;
2. training checks passed in all;
3. screen checks passed in all.
All three are pooled over runs. A candidate is rejected, whatever its rank, if any of
these holds:
- its screen total falls more than 1 check below round 0's v4 screen total;
- its training non-core checks passed (training checks passed in all, minus training
  core checks passed) fall more than 3 below round 0's v4 figure;
- more of its `change-contradicts-comment` runs ask first than v4's did in round 0. A run
  asks first when its first check's evidence ends "and the reply asks first".

A candidate becomes the best so far only if it is strictly ahead of the current best in
that order. If two candidates in a round tie on all three, the one with the shorter body
wins, then the one written first. Shorter means fewer body lines, counted as
`scripts/lint_skills.py` counts them (the same count as G4), then fewer characters in
the body.

**Stopping.** Stop after round 3, or sooner when a round improves nothing, or when the
best so far passes every training core check (42 of 42). If no candidate ever beats v4,
there is no winner: the result is null, and the final validation is not run.

**Final validation, once, after the winner is frozen.** Copy the winner's text from its
iteration's `skill-snapshot/` back to `skill/code-comments-v5/SKILL.md`, then run:
- the held-out cases: winner, v4 and bare; Haiku 3 runs, Sonnet 2 runs;
- all 11 hygiene cases: winner and v4; Haiku 3 runs, Sonnet 2 runs;
- the training cases on Sonnet: winner, v4 and bare; 2 runs.

**Who sees what.** The held-out cases guard against overfitting only if no candidate
writer has seen them (see "Held-out exposure during the builds" in
[../README.md](../README.md)).
- A candidate writer reads this README, [eval/CASES.md](eval/CASES.md), v4's SKILL.md,
  and the run records (`RESPONSE.md`, `grading.json`, `changes.diff`) of this climb's
  rounds and of the source runs that CASES.md cites.
- A candidate writer never opens [eval/HELD-OUT.md](eval/HELD-OUT.md),
  `eval/heldout_fm1.py`, `eval/heldout_fm2.py`, `eval/test_heldout.py`, a held-out case's
  `cases/`, `references/` or `hidden/` folder, or a final-validation iteration. Nor does it
  read the source evals' READMEs, `eval/*.md` or `grade.py`, or
  [../README.md](../README.md): they describe or grade the held-out cases.
- Nor does it open any scratch file, inside or outside the repository, that builds or
  grades held-out variants. Those of the held-out build and its review are
  `build_fm1.py`, `discriminate_fm1.py`, `probe_fm1.py`, `overlap_fm1.py`,
  `fm1-results/`, `fm2-proof/` and `adv-review/`. Each candidate writer gets a scratch
  folder of its own, not the scratchpad of the session that built the held-out cases.
- A candidate writer does not run `harness.py self-test` or `eval/test_heldout.py`: when
  a check fails, their output prints held-out grader text.
- No agent that has opened any of those writes a candidate.
- Before the final validation, scan each candidate writer's transcript for tool calls
  that name any file or folder above, counting each call once by its id. The write-up
  reports the count per writer. If any count is above 0, G2 is reported but not read as
  a blind test.
- A candidate states general rules. It names no file, function or value from a case.
  `harness.py lint` fails on any 8-word run of case text.
- A candidate whose body is more than 15 lines longer than v4's is not run (gate G4).

**Rulings and exclusions**, fixed now:
- An `overrides.json` ruling says who ruled and why, and the check's own result stays in
  the evidence. When a check is ruled wrong for one run, every run of that case in every
  arm of the comparison is re-read for the same misgrade. The write-up counts rulings per
  arm.
- Exclude and re-run a skill-arm run that `verify-reads` reports as not reading its own
  snapshot SKILL.md before its first edit.
- Exclude and re-run a run the run-limits guard stopped before it wrote something its
  case grades: its edits, or `RESPONSE.md` in a case with a reply check. Keep, and grade
  as it stands, a run the guard stopped only from writing a reply its case does not
  grade.
- Exclude and re-run a run whose transcript shows a model other than its iteration's.
- An excluded run moves to `iterations/<iteration>/excluded-runs/<case>-<arm>-run-K/`
  with an `EXCLUDED.txt` that says why. The re-run keeps the run number.
- No other run is excluded. A run that did badly is graded as it stands.

**Run agents.** Each run agent is a fresh agent of the iteration's model. It reads its
task from the run's `prompt.txt`, as in #50. Until the `prepare` prompt says so itself,
tell it to make every file change, and write `RESPONSE.md`, with the file-writing tools
at the absolute path the prompt gives. The harness records no model id, so each
iteration's name says the model.

**Run budget.** At most 70 runs for round 0, 40 per candidate (360 for three full
rounds), and 290 for the final validation with the 8 held-out cases: about 720 in all.
Each held-out case added later raises the last figure by 15 runs.

## Gates

All four are required before the shipped skill changes.

- **G1, training, Haiku.** The winner's training core checks passed are more than v4's
  and at least the bare model's (round 0). Its training non-core checks passed are no
  more than 3 below v4's.
- **G2, held out, Haiku and Sonnet pooled.** The winner's core checks passed are at least
  v4's, and its checks passed in all are at least v4's. No held-out case has 2 or more
  fewer full-mark runs for the winner than for v4, and no held-out case has 2 or more
  fewer core checks passed for the winner than for v4.
- **G3, hygiene, each model.** The winner's mean per-run pass rate is at least v4's
  minus 1.0 point. No hygiene case has 2 or more fewer checks passed for the winner than
  for v4.
- **G4, the skill file.** The description is v4's, word for word. `harness.py lint` and
  `self-test` pass. The body is at most 15 lines longer than v4's (76 lines, counted as
  `scripts/lint_skills.py` counts them, so at most 91).

**If a gate fails**, the result is null, and the plugin does not change. The write-up
still reports every figure, which gate failed and by how much. If all four pass, the
winner is a candidate for the plugin, and the user decides, as for every incubator skill.

## Limits known in advance

- **Few runs.** 3 Haiku runs per training cell and 2 per screen cell can show only large
  effects. A lead of one or two checks is inside run-to-run variation.
- **The screen margin is tight.** It is 1 check, while v4's own runs on
  `issue-pointer-beside-reason` ranged from 4/6 to 6/6 in hygiene iteration 5. A good
  candidate may be rejected by chance. This errs toward keeping v4.
- **G1 reuses the selection runs.** The winner is the best of up to nine candidates on
  the very runs G1 reads, so G1 overstates it. G2, G3 and the Sonnet training runs are
  fresh.
- **The screen cases are part of the final hygiene set.** For those five, G3 is not
  independent of selection.
- **The old held-out pairs had no headroom for v4.** On the four copied held-out cases
  v4 passed every check in every run of their source evals (Haiku 69 of 69, Sonnet 46 of
  46). There, G2 can show harm but not a gain. Whether v4 fails any of the four held-out
  cases built for this climb is a hypothesis: no model has run them.
- **Small fixtures, agent-built.** Each case has a few files, written by an agent, none
  from a real repository.
- **Agent rulings.** Rulings on heuristic checks are made by agents, not a human.
- **One model family.** Haiku and Sonnet only.
- **Activation is not tested.** Skill arms are told to read the skill first. The
  description does not change, but whether the edited body changes activation is
  untested.
- **A different prompt for the hygiene cases.** They run through the incubator harness's
  prompt, not the hygiene eval's own, so their scores do not compare directly with
  hygiene iteration 5.
- **Checks outside the fingerprint.** The harness fingerprints `eval/grade.py` but not
  the files it loads: the source `grade.py` files, `scripts/stale_refs.py`,
  `eval/heldout_fm1.py` and `eval/heldout_fm2.py`. `drift()` in `eval/grade.py` pins all
  of them, and `tests/test_incubator.py` fails if a copy or a pinned file changes.
- **Setup exposure.** The setup agent read the source `grade.py` files, which hold the
  held-out checks, and the held-out cases' case.yaml name and `held_out` lines. It opened
  no other held-out file, and it writes no candidate.
- **Build exposure.** The agents that built the four new held-out cases, the agent that
  reviewed them and the agent that fixed the review's findings opened held-out cases in
  full. None of them writes a candidate. [eval/HELD-OUT.md](eval/HELD-OUT.md) records
  what each read.

## Running each step

From the repository root:

```sh
TRAIN=request-quotes-stale-docstring,request-quotes-true-docstring,stale-cents-comment,true-cents-comment,docs-sync-keeps-requirements,positional-columns-in-sql,positional-columns-in-sql-pointer,sort-relied-on-elsewhere,stale-constraint-elsewhere,dispatched-by-name
SCREEN=no-invented-reason,issue-pointer-beside-reason,change-contradicts-comment,reason-only-in-test,capture-supported-reason
HYGIENE=$SCREEN,clause-goes-stale,comment-only-preserve,no-issue-tag-routine,rename-stale-refs,retry-cap-elsewhere,routine-edit-no-noise

# Checks before any run
python -B incubator/harness.py self-test code-comments-v5
python -B incubator/harness.py lint code-comments-v5
python -B -m unittest tests.test_incubator
# The held-out variants, run apart because they describe held-out cases
python -B -m unittest discover -s incubator/code-comments-v5/eval -p "test_*.py"

# Round 0: v4 and bare on training, v4 on the screen (Haiku)
python -B incubator/harness.py prepare code-comments-v5 --iteration round-0-haiku --arms shipped_skill,without_skill --runs 3 --cases $TRAIN
python -B incubator/harness.py prepare code-comments-v5 --iteration round-0-haiku --arms shipped_skill --runs 2 --cases $SCREEN
#   give each prompt in eval/iterations/round-0-haiku/runs.json to a fresh Haiku agent
python -B incubator/harness.py grade code-comments-v5 --iteration round-0-haiku
python -B incubator/harness.py verify-reads code-comments-v5 --iteration round-0-haiku TRANSCRIPT_DIR
python -B incubator/code-comments-v5/eval/score.py round-0-haiku

# Each candidate (round N, letter a, b or c): write it into skill/code-comments-v5/SKILL.md,
# then run both prepare calls before writing the next candidate (prepare snapshots the file)
python -B incubator/harness.py lint code-comments-v5
python -B incubator/harness.py prepare code-comments-v5 --iteration round-N-a-haiku --arms with_skill --runs 3 --cases $TRAIN
python -B incubator/harness.py prepare code-comments-v5 --iteration round-N-a-haiku --arms with_skill --runs 2 --cases $SCREEN
#   run, grade and verify-reads as above
python -B incubator/code-comments-v5/eval/score.py round-N-a-haiku

# Final validation, after copying the winner's snapshot back into skill/code-comments-v5/SKILL.md
python -B incubator/harness.py prepare code-comments-v5 --iteration final-heldout-haiku --arms with_skill,shipped_skill,without_skill --runs 3 --split held-out
python -B incubator/harness.py prepare code-comments-v5 --iteration final-heldout-sonnet --arms with_skill,shipped_skill,without_skill --runs 2 --split held-out
python -B incubator/harness.py prepare code-comments-v5 --iteration final-hygiene-haiku --arms with_skill,shipped_skill --runs 3 --cases $HYGIENE
python -B incubator/harness.py prepare code-comments-v5 --iteration final-hygiene-sonnet --arms with_skill,shipped_skill --runs 2 --cases $HYGIENE
python -B incubator/harness.py prepare code-comments-v5 --iteration final-train-sonnet --arms with_skill,shipped_skill,without_skill --runs 2 --cases $TRAIN
#   run, grade and verify-reads each, then:
python -B incubator/code-comments-v5/eval/score.py final-heldout-haiku final-heldout-sonnet   # G2, pooled
python -B incubator/code-comments-v5/eval/score.py final-hygiene-haiku                        # G3, Haiku
python -B incubator/code-comments-v5/eval/score.py final-hygiene-sonnet                       # G3, Sonnet
python -B incubator/code-comments-v5/eval/score.py final-train-sonnet                         # reported, no gate
```

Reading `score.py`'s output for the rules above:
- G1 and selection: `groups.train.core.passed`, then `groups.train.all.passed`, then
  `groups.screen.all.passed`. Training non-core checks passed are
  `groups.train.all.passed` minus `groups.train.core.passed`.
- The ask-first reject: count the runs whose grading.json evidence says so, for example
  `grep -l "and the reply asks first" incubator/code-comments-v5/eval/iterations/<iteration>/change-contradicts-comment/*/run-*/grading.json`.
- G2: `groups.heldout.core.passed`, `groups.heldout.all.passed`, and each held-out
  case's `per_case.<case>.full_mark_runs` and `per_case.<case>.core_passed`.
- G3: `groups.hygiene.all.mean_pass_rate` (a fraction, so 1.0 point is 0.010), and each
  hygiene case's `per_case.<case>.passed`.
- `ungraded_runs` must be 0 before any figure is used.
