# Long-horizon cheap-implementer pilot: results (2026-11-08)

Issue [#43](https://github.com/AndrewGodlewsky/code-comments/issues/43). Parent:
[#37](https://github.com/AndrewGodlewsky/code-comments/issues/37). Design and decision rules:
[pilot-preregistration.md](pilot-preregistration.md), including every deviation. Harness:
[evaluation/pilot/README.md](../../evaluation/pilot/README.md). Run data:
[evaluation/pilot/runs/full-2026-11-08/](../../evaluation/pilot/runs/full-2026-11-08/).

## The answer in one paragraph

Six real narwhals features were built in a row, and each arm kept building on its own
code. Here, Haiku 5.5 did **not** erode the codebase faster than Sonnet 5.5. The
pre-registered outcome is **rule 1, "Haiku within noise of Sonnet"**: the gap is −1, so
Haiku-plain scored one point better.

The comments-research stop rule also fires. The lean comments skill was no better than a
one-sentence "keep the codebase clean" instruction (E 6 against 5). Under the
pre-registration, the comments efficacy research ends, and only the hygiene skill (#45)
goes forward.

Haiku-plain was the cheapest arm per passing step: **$0.077, against $0.321 for Sonnet**,
about 4×. Adding a Sonnet review to Haiku cost almost as much as Sonnet and did no better.

**How strong this is:** it is weak evidence of no difference, not evidence that the arms
are equal. Only 1 of the 6 steps separated the arms, and no arm produced a single
regression (see [What the instrument could see](#what-the-instrument-could-see)).

## What was run

- **Repository:** narwhals, at a start commit before six merged PRs (#3996, #4001,
  #3815, #4038, #4017, #3915). Each step's real PR tests were hidden from the
  implementer.
- **Arms:** haiku-plain, haiku-instruct, haiku-skill (the lean `code-comments` skill),
  haiku-review (Haiku implements, Sonnet reviews read-only, Haiku revises once) and
  sonnet-plain.
- **Size:** 2 repetitions × 6 steps per arm, which is 12 step-attempts per arm and 84
  model sessions.
- **Models and harness:** `claude-haiku-5-5` and `claude-sonnet-5-5`, through headless
  Claude Code 2.1.319, in Docker containers. Sessions had network access for the API,
  with package indexes disabled. Scoring ran with no network.
- **Credential and limits:** an OAuth subscription token, a $30 cap, and $1.50 and
  1800 s per session.
- **Run IDs:** `run.json` has `run_id`. The harness hash changed once, at the resume, and
  both hashes are recorded in its `harness_changes`.
- **Timeline:** started 2026-11-08 12:19. It crashed at step 6 at 13:46 and resumed at
  14:06, after a parser fix (see Deviations). It finished at 14:22.

## Results

### Per arm (pre-registered scoring)

| Arm | Passing | Failed | Regression events | High-churn steps | **E** | Sum of excess churn | Cost | Cost / passing step |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| haiku-plain | 7/12 | 5 | 0 | 0 | **5** | −74 | $0.54 | **$0.077** |
| haiku-instruct | 7/12 | 5 | 0 | 0 | **5** | −94 | $0.80 | $0.114 |
| haiku-skill | 7/12 | 5 | 0 | 1 | **6** | −74 | $0.87 | $0.124 |
| haiku-review | 6/12 | 6 | 0 | 0 | **6** | −37 | $1.69 | $0.281 |
| sonnet-plain | 6/12 | 6 | 0 | 0 | **6** | −93 | $1.93 | $0.321 |

E = failed steps + regression events + high-churn steps. Lower is better.

### Decision rules

| Rule | Result | Why |
| --- | --- | --- |
| 1. Haiku within noise of Sonnet | **Fires** | The gap is −1 (≤ 2). Haiku-plain is no worse than Sonnet on failed steps (5 against 6), regressions (0 against 0) or high churn (0 against 0) |
| 2. Comments clearly beat instruction | Doesn't fire | E(skill) = 6, which is not ≤ E(instruct) − 3 = 2 |
| 3. Review closes the gap cheaply | Doesn't fire | There is no gap to close (it needs ≥ 3), and review costs 0.88× Sonnet per passing step (it needs < 0.6×) |
| Comments stop rule | **Fires** | E(skill) = 6 ≥ E(instruct) − 1 = 4 |

**The outcome, under the pre-registration:**
- The tangle concern isn't reproduced at this scale. Use Haiku behind tests, and park
  the erosion research.
- End the comments efficacy research, and keep only the hygiene skill (#45).

### Per step (pass or fail, and normalised churn, for repetitions 1 and 2)

| Arm | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 | Step 6 |
| --- | --- | --- | --- | --- | --- | --- |
| Real PR churn | 21 | 119 | 57 | 15 | 66 | 22 |
| haiku-plain | P29 / P22 | F75 / F82 | P43 / F56 | P15 / P15 | P65 / P82 | F21 / F21 |
| haiku-instruct | P21 / P18 | F76 / F79 | F36 / P65 | P26 / P17 | P65 / P66 | F23 / F14 |
| haiku-skill | P30 / P9 | F85 / F78 | P38 / F40 | P17 / P22 | P72 / P63 | F26 / F46 |
| haiku-review | P25 / P25 | F105 / F99 | F33 / F55 | P15 / P26 | P59 / P65 | F35 / F21 |
| sonnet-plain | P32 / P32 | F82 / F70 | F37 / F33 | P18 / P15 | P77 / P67 | F15 / F29 |

### Secondary measures (reported, not used in the decision)

| Arm | Duplication growth (r1, r2) | Complexity growth (r1, r2) | New stale references |
| --- | --- | --- | ---: |
| Reference (the real PRs) | 2 | 71 | 2 (both lint false positives) |
| haiku-plain | 1, 2 | 59, 72 | 0 |
| haiku-instruct | 3, 5 | 53, 59 | 0 |
| haiku-skill | 0, 3 | 60, 73 | 0 |
| haiku-review | 2, 2 | 64, 71 | 0 |
| sonnet-plain | 2, 1 | 58, 57 | 0 |

No arm drifted far from the reference on any secondary measure.

### Sessions

| Arm and role | Sessions | Median turns | Median wall time | Mean cost | Maximum cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| haiku-plain implement | 12 | 31 | 212 s | $0.045 | $0.091 |
| haiku-instruct implement | 12 | 35 | 220 s | $0.067 | $0.242 |
| haiku-skill implement | 12 | 36.5 | 254 s | $0.073 | $0.245 |
| haiku-review implement | 12 | 36.5 | 188 s | $0.052 | $0.178 |
| haiku-review review (Sonnet) | 12 | 3 | 17 s | $0.065 | $0.085 |
| haiku-review revise | 12 | 16 | 108 s | $0.024 | $0.053 |
| sonnet-plain implement | 12 | 12.5 | 75 s | $0.161 | $0.301 |

- Every session ended with `success`.
- No session came near the $1.50 limit, and none timed out.
- Sonnet used about a third of Haiku's turns and finished about 3× faster, at about 3.5×
  the cost per session.

**Total spend:**
- **$5.83** recorded in the run.
- **$1.05** on 12 sessions discarded after the crash.
- An unknown, small amount for the single session that crashed.
- **$0.44** for the smoke run.

That is **about $7.30** in all, against the $30 cap. All figures are Claude Code's
API-equivalent estimates, charged to a subscription.

## What the instrument could see

Read this section before using the result. The pilot was built to detect erosion
through three channels. In this run, two of them were almost silent:

1. **Regressions: none, in any arm.** Across 10 lanes and 60 step transitions, no test
   that had passed ever stopped passing. This was checked independently of the scorer,
   by recounting from the raw JUnit reports with no exclusions. Every arm could see and
   run the roughly 16,000-test suite.
   - So, with a strong test suite in reach, neither model broke earlier features.
   - It also means E measured only failed steps and high churn.
2. **High churn: one step in 60, and a false positive.** `haiku-skill` repetition 2 at
   step 6 had excess churn of 24, just over its threshold of 22.
   - A hand reading shows a careful, complete implementation of step 6's feature: a
     type-compatibility table that raises `InvalidOperationError`, with short
     explanatory comments. It is not an unnecessary rewrite.
   - Every arm's largest step stayed within the files its feature needed (see
     `diffs/`).
   - Excess churn was **negative** in every arm. The arms changed fewer lines than the
     real PRs, mostly because they built less of the feature, not because they were
     more economical.
3. **Failed steps: only step 3 separated the arms.**
   - Every lane passed steps 1, 4 and 5.
   - Every lane failed steps 2 and 6.
   - On step 3, the lanes split: the three plain Haiku variants passed 3 of 6 repetitions,
     and review and Sonnet passed 0 of 4.
   - So the whole difference in E comes from step 3 plus the one high-churn false
     positive. It amounts to 1 point.

Why every lane failed steps 2 and 6:
- **Step 2.** The defective test `test_contains_chunked` (see Deviations), plus
  `test_null_list_lit` (which every lane failed) and `test_contains_inner_dtypes_expr`
  (9 of 10 lanes). The task statement asks for "the same results and null handling as
  Polars", and these tests check a typed null list literal and nested inner dtypes. The
  statement asks for that behaviour only indirectly, if at all.
- **Step 6.** The hidden test module is the whole `contains_test.py`, and it still
  contains the step 2 tests. So a lane that failed step 2's `contains` tests also fails
  step 6. Every lane also failed `test_contains_datetime_precision_coerced`.

**The sensitivity scoring** drops `test_contains_chunked`
(`summary --exclude-test test_contains_chunked`, saved as `summary-sensitivity.json`). It
changes **no** pass, fail or decision: the lanes failed steps 2 and 6 on other tests
as well.

**Conclusion on strength.** The data are consistent with "no meaningful difference
between Haiku and Sonnet on this chain". But the chain only discriminated weakly:
- One of six steps separated the arms.
- Regressions never happened.
- The pre-registered "threats to validity" (replay divergence, six steps, a proxy
  churn threshold) all applied.

A real erosion effect of a few points of E could be missed at this scale.

## Priors against the outcome

| Prior | Prior probability | Outcome |
| --- | ---: | --- |
| A Sonnet review cuts Haiku's excess churn clearly | 70% | **False.** Review had no high-churn steps, but neither did plain Haiku. Review's mean excess churn (−3.1 per step) is not lower than plain's (−6.2) |
| Haiku plain erodes measurably faster than Sonnet | 55% | **False.** The gap is −1 |
| Instruction-only cuts churn about as much as the skill | 65% | **True.** High-churn steps were 0 for instruct and 1 for skill |
| The comments skill reduces regressions in earlier features | 30% | **False.** No arm had any regressions |
| The comments arm clearly beats instruction-only | 20% | **False** |

## Deviations that affect this run

All of these are recorded in full, with dates, in the pre-registration:

- **Package installs blocked** (from the smoke run). Every session sets
  `PIP_NO_INDEX=1` and `UV_OFFLINE=1`, and every arm's prompt says not to install
  packages.
  - It held. All 9 flagged commands in the full run were false matches (`grep uv.lock`,
    `pip show`, `uv --version`) or one offline `uv run`.
  - Without the block, every Haiku session in the smoke run had installed packages.
- **Runner crash at step 6.**
  - The cause: a stream-json event carried `message` as a string.
  - The fix (commit `f0d8be5`): the parser now skips such events, and the runner now
    records each lane's finished work even when another lane crashes.
  - The 8 unrecorded step-6 lanes were moved, unopened, to `discarded-crash/`, and
    rerun from a clean reset. The rerun is the result used.
- **A hidden test tied to private names** (`test_contains_chunked`, step 2, and so step
  6). The pre-registered scoring stays primary. A sensitivity scoring without the test
  is reported above, and its result is identical.

## Lessons for the next study

These come from what actually went wrong or right here. They are not hypotheses.

1. **Check every hidden test for private-symbol coupling before running.**
   - What happened: one `monkeypatch.setattr("narwhals._arrow.utils._LIST_BLOCK_VALUES", …)`
     made a step impossible to pass. Running the oracle can't catch this, because the
     oracle defines the names.
   - Check to do: search each step's test diff for `narwhals._` and for `monkeypatch`
     or `mocker` on private names.
2. **Don't let two steps share a hidden test module.**
   - What happened: steps 1, 2 and 6 all change `contains_test.py`. Since the whole
     module was scored, a step 2 failure also failed step 6.
   - Fix: score only the tests a step adds or changes, or pick PRs with separate test
     files.
3. **Check that each step's tests can be passed from its task statement.**
   - What happened: a step that every arm fails can't separate the arms. Steps 2 and 6
     gave no information here.
   - Check to do: before the paid run, have a strong model attempt each step once,
     and treat a step nobody can pass as a task-statement problem to fix first.
4. **With the full test suite visible, regressions may never happen.**
   - To measure erosion, measure something the agent can't check for itself: hidden
     regression tests, maintainability review, or the cost of a later change.
5. **Block package installs in model containers by default.** Without the block, Haiku
   installed unaudited packages next to the credential in every smoke-run session.
6. **Expect Haiku to need far more turns than Sonnet.** Its turns are cheap enough that
   it still came out about 4× cheaper per passing step. But it took about 3× as long,
   which matters if wall time is the constraint.

## What this changes

- **For the product (see [intent.md](../../intent.md)):** the hypothesis that inline
  comments help less capable models over a long project gained **no support** here. On
  one repository and six steps, the cheaper model needed no help, and the skill did no
  better than one sentence of instruction. Together with tournament round 1 (#26),
  which was also a null result, this points toward the lean hygiene skill (#45), not a
  larger comments-efficacy programme.
- **What remains open:**
  - Whether erosion appears over longer chains, on repositories with weaker test
    suites, or in measures the agent can't check for itself (lesson 4).
  - This pilot can't rule out an effect under those conditions.

## Reproduce

```text
python -m evaluation.skill_eval.pilot summary --out evaluation/pilot/runs/full-2026-11-08
python -m evaluation.skill_eval.pilot summary --out evaluation/pilot/runs/full-2026-11-08 --exclude-test test_contains_chunked
```

`summary` needs the JUnit reports. Unpack `junit.tar.gz` in the run folder first. The
raw session traces are in `sessions.tar.gz`. The diffs that each arm wrote at each step,
and the reviewer's diffs, are under `diffs/` and `reviews/`.
