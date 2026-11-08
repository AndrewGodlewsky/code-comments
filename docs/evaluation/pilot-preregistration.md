# Long-horizon cheap-implementer pilot: pre-registration (2026-11-07)

Issue #37, sub-issue #38. Design source:
[path-forward-2026-11-07.html](../path-forward-2026-11-07.html), option 1.

This file is committed **before any paid run**. The commit that adds it is recorded
on #37. Any later change to the design, the metrics, the thresholds or the decision
rules goes in the **Deviations** section at the end, with a date and a reason, and
the report lists every deviation. The thresholds below turn the memo's soft phrases
("within noise", "clearly beats", "half the gap") into numbers, so the result cannot
be reinterpreted afterwards.

## Question

Six real features are built in a row on one real repository, and each arm keeps
building on its own code. Does a cheap implementer (Haiku 5.5) erode the codebase
faster than Sonnet 5.5? Which of these closes the gap at the lowest cost per passing
step?

- a plain instruction
- the lean comments skill
- a Sonnet review at each step

**This is a pilot:** one repository and two repetitions. It can show a direction and
stop spending on a dead end. It cannot prove an effect. No significance tests are
reported as evidence. Counts are reported for every arm and every repetition.

## Setup

**Repository.** [narwhals](https://github.com/narwhals-dev/narwhals) (see
[candidate-repos.md](../research/candidate-repos.md)). Every public-API change has to
be repeated across backends, which invites both duplication and cross-module mistakes.
The repository is cloned, installed and run **only inside a container**, after the
dependency vulnerability scan in #39. Model sessions that run code also run inside
that container. Nothing from the repository runs on the host.

**Steps (#40).** Six merged PRs, applied in merge order.

- **Selection criteria:**
  - merged after 2026-06-30 (after the models' training cutoff);
  - changes code under `narwhals/`, preferably in two or more files;
  - adds or changes tests that exercise the change **through the public API**;
  - changes 20 to 400 non-test source lines;
  - changes no dependencies;
  - is not a pure refactor, docs change or CI change.
- **Start commit:** the parent of the first selected PR.
- **The oracle chain:** the start commit plus the six real PR diffs, and nothing else
  from upstream.
- **When a step is dropped.** A step is dropped, and the drop is listed, if:
  - its diff does not apply to the oracle chain at that point;
  - its new tests fail on the oracle chain;
  - the existing suite fails on the oracle chain and the failure cannot be excluded as
    a known pre-existing failure.
- **Fewer valid steps.** If fewer than six PRs survive, the next qualifying PR is
  added. Fewer than four valid steps means the pilot is not run as designed, and the
  user is asked.

**Task statement.** One per step, written from the PR's title, description and linked
issue. It describes the required public behaviour and leaves out the implementation.
The PR's new tests are **hidden** from the implementer. The existing tests are
visible, and the implementer may write its own tests. One statement per step is used
by every arm, and all six are committed before the smoke run.

**Arms (5).** The model IDs are `claude-haiku-5-5` and `claude-sonnet-5-5`. Every
session is one headless Claude Code session (`claude -p`), using the harness in
`evaluation/skill_eval/live.py`.

| Arm | Implementer | Extra |
| --- | --- | --- |
| `haiku-plain` | Haiku | none |
| `haiku-instruct` | Haiku | One fixed sentence added to the task: *"Keep the codebase clean: reuse what already exists, change only what the feature needs, and don't rewrite working code."* |
| `haiku-skill` | Haiku | The lean comments skill (`skill-variants/lean/code-comments/SKILL.md`), installed as a plugin the way earlier runs installed it |
| `haiku-review` | Haiku | After Haiku finishes, a Sonnet session sees the step's diff, the task statement and a fixed churn checklist (unnecessary rewrites, duplication of existing helpers, unrequested restructuring, behaviour drift, stale comments). It can comment but not edit. Haiku then gets **one** revision session with those findings. |
| `sonnet-plain` | Sonnet | none |

**Repetitions.** 2 per arm. That is 5 arms × 2 reps × 6 steps = **60 implementer
sessions**, plus 12 Sonnet reviews and 12 Haiku revision sessions in `haiku-review`.
The two reps differ only in sampling. Run order is interleaved: step *k* of every arm
and rep runs before step *k*+1 of any of them. If the budget runs out, every arm is
then cut off at the same step.

**Session limits.** These are set from the smoke run (#42) and frozen in the
Deviations section before the full run: a per-session timeout, a per-session
`--max-budget-usd` and a total cap. The total cap needs the user's approval; the
suggestion is $60. A session that fails because of the harness (an API error, a
timeout before any edit, or a container fault) is retried **once** and the retry is
recorded. A second failure is scored as a failed step with no code change.

**Carrying state forward.** Each arm and rep keeps its own working tree from step to
step, whatever the outcome of a step. A failed step is not repaired, and the oracle
diff is never substituted. Tests the implementer wrote stay in the tree, but they are
excluded from the churn and erosion metrics.

## Metrics

All metrics are computed offline from the stored working trees, and can be computed
again later. A step-attempt is one arm, one rep and one step, so there are 12
step-attempts per arm.

| Metric | Definition |
| --- | --- |
| **Pass** | The step's hidden PR tests all pass on the arm's tree after the step. |
| **Regression** | A test that passed on the arm's tree **before** the step and fails **after** it. The test set is the existing suite plus every earlier step's hidden tests. One regression event is counted per step-attempt with at least one such test, and the number of tests is also reported. |
| **Excess churn** | Normalised changed code lines in non-test files under `narwhals/` (an AST round-trip with comments and docstrings removed, as in `churn.py`), minus the same count for the real PR diff. It is measured against the arm's own state before the step. |
| **High-churn step** | Excess churn ≥ max(10 lines, the real PR's own churn). In other words, the arm rewrote at least twice what the developers changed, and at least 10 extra lines. |
| **Duplication growth** | Duplicated normalised blocks of at least 6 consecutive lines across `narwhals/` source, measured at step 6, minus the count at the start commit. It is compared with the oracle chain's growth. |
| **Complexity growth** | Total cyclomatic complexity over `narwhals/` functions (a stdlib `ast` count of branches and boolean operators, plus 1 per function), measured at step 6, minus the start commit. It is compared with the oracle chain's growth. |
| **Stale references** | New findings from the stale-reference lint (#44) in `--diff` mode at each step, summed over all six steps. The lint's false-positive rate on the start commit is reported alongside. |
| **Cost per passing step** | Total USD across every session in the arm, including reviews and revisions, divided by its number of passing step-attempts. The cost is the API-equivalent figure reported by Claude Code. |

**Erosion score (decision metric).** *E* = failed steps + regression events +
high-churn steps, counted over an arm's 12 step-attempts. It ranges from 0 to 36,
and lower is better. The **gap** is *E*(`haiku-plain`) − *E*(`sonnet-plain`).

Duplication, complexity and stale references are **secondary**. They are reported
for every arm but do not enter the decision rules, because the pilot cannot tell how
much noise they carry.

## Decision rules

The rules are applied in this order, which matches the flowchart in the memo.

1. **Haiku within noise of Sonnet.** The gap is ≤ 2, **and** on each of the three
   counts (failed steps, regression events, high-churn steps) Haiku plain exceeds
   Sonnet by at most 1.
   → Your tangle concern isn't reproduced at this scale. Use Haiku behind tests and
   park the erosion research. Rules 2 to 4 are still computed and reported, but
   they do not drive the decision.
2. **Comments clearly beat instruction-only** (only if rule 1 did not fire). Both
   of these hold:
   - *E*(`haiku-skill`) ≤ *E*(`haiku-instruct`) − 3.
   - Either high-churn steps or regression events are at most half the
     instruction-only count, where that count is at least 2.

   → The thesis survives where it matters. Fund a powered option 3 on 2 or 3
   repositories.
3. **Review closes the gap cheaply** (only if rules 1 and 2 did not fire). All
   three hold:
   - The gap is ≥ 3.
   - *E*(`haiku-review`) ≤ *E*(`sonnet-plain`) + gap / 2.
   - The review arm's cost per passing step is < 0.6 × `sonnet-plain`'s.

   → Judgment is the lever. Build option 4, with comments as a supporting part.
4. **Otherwise** → hygiene skill only, and park the research.

**Ending the comments research.** Regardless of the order above, if
*E*(`haiku-skill`) ≥ *E*(`haiku-instruct`) − 1, the comments arm is "no better than
instruction-only". The comments efficacy research then ends, and only the hygiene
skill (#45) is kept. This is the memo's second stop rule, and it applies even when
rule 3 also fires.

## Priors (written before any data)

These are the author's judgment calls, made in the memo. Here they are tied to the
measures above.

| Prior | Probability | Counts as true if |
| --- | ---: | --- |
| A Sonnet review cuts Haiku's excess churn clearly | 70% | `haiku-review` has at most half of `haiku-plain`'s high-churn steps, where that count is at least 2; or its mean excess churn is at least 50% lower |
| Haiku plain erodes measurably faster than Sonnet over 6 steps | 55% | The gap is ≥ 3 (rule 1 does not fire) |
| Instruction-only cuts churn about as much as the skill does | 65% | High-churn steps differ by at most 1 between `haiku-instruct` and `haiku-skill` |
| The comments skill reduces regressions in earlier features | 30% | `haiku-skill` has at least 2 fewer regression events than `haiku-plain` |
| The comments arm clearly beats instruction-only | 20% | Rule 2's two conditions hold, judged on their own, whether or not rule 1 fires |

## Offline self-test (before any paid run)

The runner (#41) must pass these checks offline, inside the container:

- **Oracle arm:** it applies the real PR diffs. It must pass every valid step, with
  zero regressions and zero excess churn, and its duplication and complexity growth
  must equal the reference values.
- **Null arm:** it changes nothing. It must fail every step that adds new behaviour,
  and it scores zero churn.
- Unit tests cover each metric on small fixtures.

## Threats to validity (accepted in advance)

- **Replay divergence.** An arm whose code drifts from the real history may fail later
  hidden tests for reasons unrelated to quality. Public-API grading reduces this.
  The report also lists, for each failed step, whether the failure follows an earlier
  failed step in the same arm.
- **One repository**, so the results may not generalise.
- **Six steps.** Published erosion trends appear over 4 to 8 steps, so a real effect
  could be missed.
- **High-churn threshold.** The threshold is a proxy, since some refactoring is
  legitimate. The report includes a hand-read sample of the largest-excess diffs from
  each arm.

## Deviations

Smoke-run limits are recorded here before the full run. Each entry is dated and was
written before any model session ran.

- **2026-11-07, source path.** narwhals keeps its code in `src/narwhals/`, not
  `narwhals/`. Every rule and metric above that names `narwhals/` means
  `src/narwhals/`.
- **2026-11-07, backends tested.** The runtime image installs pandas, polars,
  pyarrow, duckdb, sqlframe and dask (#39). Every run, oracle and arm, uses the
  constructor set in `evaluation/pilot/chain/constructors.env`. pyspark, modin, cudf
  and ibis are not installed, so their code paths are not tested. Code an arm writes
  for those backends counts towards churn, but the tests can't catch its mistakes.
- **2026-11-07, step 4011 dropped.** The fifth PR in merge order, #4011 (floor
  division by zero), does not apply to the oracle chain:
  `error: patch failed: src/narwhals/_pandas_like/series.py:16`. Its import-list
  context depends on an upstream commit outside the chain. By the drop rule it was
  dropped, not adapted, and the next qualifying PR in merge order, #3915, became
  step 6. The diff is kept in `evaluation/pilot/chain/dropped/`.
- **2026-11-07, files outside `src/narwhals/` and `tests/`.** Two steps change other
  files. #4001 changes `tests/conftest.py` so the Dask constructor keeps list
  columns. #3815 changes two API-reference pages under `docs/` and the test plugin
  in `packages/test-plugin/`. All of these stay in the oracle chain. For the arms,
  `tests/conftest.py` and `packages/test-plugin/` count as test support: they are
  hidden with the PR's tests, applied with them at scoring, and excluded from churn.
  The `docs/` pages are not scored.
- **2026-11-07, chain validated.** All six steps apply in order, each step's own
  tests pass, and the full suite has no failures after any step: from 15906 passed at
  the start commit to 16266 passed after step 6. The details are in
  `evaluation/pilot/README.md`.
- **2026-11-08, package installs blocked (from the smoke run, #42).** Every Haiku
  session in the smoke run installed PyPI packages the #39 audit didn't cover (ibis,
  pyspark, `jdk4py`, `ruff`) into `/tmp` virtualenvs, in a container that also holds
  the credential. Sonnet installed none. From now on, every session container sets
  `PIP_NO_INDEX=1` and `UV_OFFLINE=1`, and every arm's prompt ends with the same
  sentence: *"The environment is already set up. Don't install packages; package
  downloads are disabled."*
  - This is a change to the committed task statements, applied equally to all arms.
  - An agent can still override the settings deliberately. The flagged-Bash count keeps
    recording any attempt, and every attempt is reported.
  - The smoke-run results were produced without this change. They are a harness check
    only and are not pooled with the full run.
- **2026-11-08, full-run limits frozen (from the smoke run, #42).**
  - The smoke run cost $0.44 for 7 sessions. Its most expensive session was $0.14 and
    its longest took 422 s.
  - **Total cap:** $30, approved by the user, who allowed up to $45 if needed. Raising
    the cap does not change the design: the run resumes from its saved results, and
    run order is still interleaved by step.
  - **Per session:** `--max-budget-usd 1.50`, with a 1800 s timeout.
  - **Run settings:** 2 repetitions, steps 1–6, 3 lanes at a time.
  - **Credential:** an OAuth token, so the cost figures are Claude Code's API-equivalent
    estimates.
