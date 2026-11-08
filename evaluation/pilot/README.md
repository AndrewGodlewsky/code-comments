# Pilot container (#37, #39)

The narwhals pilot runs only inside this container. Nothing from narwhals is installed
or run on the host.

| File | Purpose |
| --- | --- |
| `Dockerfile` | `scan` target: clones narwhals at the start commit and exports hash-pinned requirements from its `uv.lock`, without installing anything. `runtime` target: installs exactly those hashes, then narwhals itself (editable, no dependencies). |
| `scan.sh` | Builds `scan`, runs `pip-audit` on the export, and writes the results to `scan/`. |
| `scan/` | The audited `requirements.txt`, the `pip-audit` JSON, and the image and base digests. |

Order: run `scan.sh`, read the result, and build `runtime`
(`docker build --target runtime -t code-comments-pilot:runtime evaluation/pilot`)
only when the audit is clean or the user has decided on each finding.

## Scan result, 2026-11-07

- **Start commit:** narwhals `7d3a326100decf6258cc5386fbb5ad70990b36bd`, the parent of
  PR #3996's merge commit.
- **Tools:** uv 0.13.5 and pip-audit 2.10.1 (the PyPI advisory service, via
  pip-audit's default), on the digest-pinned `python:3.12-slim` base.
- **Scope:** narwhals' `core` and `tests` dependency groups plus the `dask` extra.
  The backends are pandas, polars, pyarrow, duckdb, sqlframe and dask. pyspark,
  modin, cudf and ibis are excluded, so tests for those backends are skipped.
- **Result:** 45 pins exported, 38 audited, **0 known vulnerabilities**. The other 7
  (colorama, exceptiongroup, importlib-metadata, pytz, tomli, tzdata, zipp) carry
  environment markers for Windows or Python below 3.12, so they are not installed
  in this image.
- **Main versions:** pandas 3.0.6, polars 1.44.2, pyarrow 25.0.1, duckdb 1.5.5,
  dask 2026.8.0, sqlframe 4.4.0, numpy 2.5.3, pytest 9.1.1, hypothesis 6.168.3.

## Oracle chain (#40), 2026-11-07

`chain/` holds the six PR diffs, in order, and `constructors.env` sets the backends
every test run uses. `validate_chain.sh OUT_DIR` applies the diffs one at a time in
the runtime container, runs each step's own tests and then the full suite, and writes
JUnit XML and a summary to `OUT_DIR`. The task statements every arm receives are in
`tasks.md`.

| Step | PR | Change | Own tests | Full suite after the step |
| ---: | --- | --- | --- | --- |
| start | — | narwhals `7d3a3261` (2.26.0) | — | 15906 passed, 353 skipped, 998 xfailed |
| 1 | #3996 | `list.contains` null handling on lazy backends | 23 passed | 15924 passed |
| 2 | #4001 | `list.contains` on PyArrow, pandas and Dask; Dask `List` cast | 534 passed | 16035 passed |
| 3 | #3815 | `DataFrame.cast` and `LazyFrame.cast` | 47 passed | 16082 passed |
| 4 | #4038 | Polars-consistent errors for `sort` and `top_k` flags | 176 passed | 16172 passed |
| 5 | #4017 | `list.len/get/min/max/mean/median/sum/sort` on Dask | 184 passed | 16183 passed |
| 6 | #3915 | `InvalidOperationError` for mismatched `list.contains` items | 206 passed | 16266 passed, 358 skipped, 993 xfailed |

There were no failures in any run. A full-suite run takes about 19 seconds
(`-n 8 -p no:randomly`).

PR #4011 was fifth in merge order but its diff does not apply to the chain, so it was
dropped and #3915 was added (see the pre-registration's Deviations). Its diff is in
`chain/dropped/`.

Notes for the runner (#41):

- Steps 1, 2 and 6 all change `tests/expr_and_series/list/contains_test.py`. During
  a session, that file is held at its pre-step version, and the step's version is
  applied at scoring.
- Hidden test support also includes step 2's `tests/conftest.py` and step 3's
  `packages/test-plugin/` change.
- After scoring, the step's tests stay in the arm's tree, so later steps can detect
  regressions against them.

## Stale-reference lint (#44), 2026-11-07

`scripts/stale_refs.py` (stdlib only, tests in `tests/test_stale_refs.py`) reports
comments and docstrings that name an identifier, dotted path, call, file or flag that
no longer exists in the tree. The pilot uses its `--base-dir` mode, which reports only
findings that are new since the step's starting tree. It runs on narwhals inside the
container, with `--network none`.

| Check | References | Findings | True | False positives |
| --- | ---: | ---: | ---: | --- |
| narwhals start commit, `--only src/narwhals` | 1906 | 44 | 3 | 41 (2.2% of references) |
| This repository | 265 | 0 | 0 | 0 |
| Skill-eval reference solutions, diff mode (20 cases) | — | 0 | 0 | 0 |
| Skill-eval model end states, diff mode (720 runs) | — | 0 | 0 | 0 (53 before the fixes below) |

- **The 3 true findings in narwhals.** `_compliant/dataframe.py:351` and `:361`
  name `_evaluate_into_expr`, which is now `_evaluate_expr`. `_compliant/group_by.py:125`
  names `CompliantExpr._depth`, which is not defined.
- **The remaining false positives** are prose words and examples: `Narwhal`, `Other`,
  `leaf` in an example, `min_by`/`max_by` as Polars names, and names from other
  libraries such as `WindowsPath` and `ArrowDType`. Tuning took the count from 151 to 44.
- **The 720 model end states.** These are the final trees of the regraded Sonnet and
  Haiku skill-eval runs, rebuilt from their traces. All 53 earlier findings were false
  positives of three kinds:
  - a name the task's docs put in backticks but the code no longer reads (`issued_at`);
  - a plural of a known name (`event_ids`, "`date`s");
  - a method of a builtin type (`str.isalnum`).

  The lint now accepts all three. The single semantic bad claim in those runs
  (`sort-for-dedup`, Haiku v1) does not name missing code, so the lint does not catch
  it. As expected, the lint catches name-level staleness, not wrong reasoning.
- **A bug the tests caught.** In JavaScript-like files, a comment containing a quote
  or backtick was read as the start of a string. One combined comment-or-string scan
  fixed it.

## Runner (#41)

`evaluation/skill_eval/pilot.py` runs the arms on the host and starts containers.
`evaluation/skill_eval/pilot_inner.py` runs inside `runtime` and does the git work and
scoring. The `agent` target adds Claude Code 2.1.319 as uid 1000. Build it with
`docker build --target agent -t code-comments-pilot:agent evaluation/pilot`.

```
python -m evaluation.skill_eval.pilot run --out DIR --arms oracle,null --reps 1
python -m evaluation.skill_eval.pilot summary --out DIR
python -m evaluation.skill_eval.pilot cleanup --out DIR
```

- Each lane (arm and repetition) gets its own Docker volume holding a narwhals checkout.
  Step 0 resets it to the start commit. Each step after that scores the work, then
  commits that step's hidden tests from the oracle tag.
- Scoring containers run with `--network none` and mount the harness and oracle chain
  read-only. Model sessions need network access to reach the API. They get the
  checkout (read-only for the reviewer), and the credential is passed by name
  (`-e ANTHROPIC_API_KEY` or `-e CLAUDE_CODE_OAUTH_TOKEN`), never by value.
- Without `--live`, the model arms run dry. They act like the null arm and write the
  redacted commands they would have run to `sessions/{label}.dry.json`, so the plumbing
  can be tested for free. `--live` needs `--credential`, the matching
  environment variable, and `--cap`. The cap is a total in USD, and each session is
  reserved against it before it starts.
- `--credential-file .env.pilot` makes the runner read the token itself, so the agent
  driving the run never sees it. The file sits at the repository root. Git ignores
  it (`.env.*`), and `.claude/settings.json` denies Claude agents opening it with
  their file tools or common shell readers. Those rules only stop accidental reads by
  Claude agents. Any program running as your Windows user, including other agent
  tools, can still read the file. Revoke the token after the run.
- `summary` prints per-arm totals (failed steps, regression events, high-churn steps,
  stale references, duplication and complexity growth, cost per passing step), the
  pre-registered decision rules, and the oracle and null self-checks.

### Offline self-test, 2026-11-08

Run with `--arms oracle,null,haiku-plain --reps 1`, where haiku-plain was dry. It
cost nothing and took 8 minutes, about 35 s per step per lane.

| Arm | Steps passed | Failed | Regressions | Excess churn | Stale refs |
| --- | --- | --- | --- | --- | --- |
| oracle | 6 / 6 | 0 | 0 | 0 | 2 |
| null | 0 / 6 | 6 | 0 | -300 | 0 |
| haiku-plain (dry) | 0 / 6 | 6 | 0 | -300 | 0 |

Every self-check in `summary` passes: the oracle passes every step with no
regressions and zero excess churn, and its duplication and complexity match the
reference. The null arm fails all six steps with zero churn. The reference churn of
the six upstream PRs is 21, 119, 57, 15, 66 and 22 normalized lines. Duplication grows
by 2 and complexity by 71 across the chain.

The oracle's 2 stale references are lint false positives. Step 1's comment in
`_spark_like/expr_list.py` names the Spark SQL functions `array_intersect` and
`typeof` in backticks, and they are not repository symbols. Read a model arm's
stale-reference count against this baseline, and check each hit by hand before
counting it.

### Smoke run (#42), 2026-11-08

This was the first live run: the five model arms on step 1, with 1 repetition, an OAuth
credential, `--cap 5` and `--max-budget 1`. It took 14 minutes, and Claude Code
estimated the cost at $0.44. That estimate is reported under OAuth too.

| Arm | Sessions | Turns | Wall time | Cost | Pass | Excess churn |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| haiku-plain | implement | 46 | 237 s | $0.044 | yes | 0 |
| haiku-instruct | implement | 58 | 422 s | $0.068 | yes | 5 |
| haiku-skill | implement | 46 | 311 s | $0.058 | yes | 13 |
| haiku-review | implement, review, revise | 41, 3, 30 | 240, 18, 193 s | $0.132 | yes | 15 |
| sonnet-plain | implement | 13 | 51 s | $0.140 | yes | 14 |

- **The harness works end to end:**
  - No session failed.
  - The model IDs resolved.
  - The reviewer was read-only and returned concrete checklist findings, and the
    revision session acted on them.
  - The skill arm got the skill. `/cce:code-comments` expanded, and its first request
    was 1,349 input tokens larger than haiku-plain's (the instruct arm's was 41 larger,
    for its one sentence). Headless output doesn't echo the expanded prompt, so the
    token count is the evidence.
- **Every Haiku session installed packages from PyPI.** The flagged-Bash count was 8–11
  per Haiku session and 0 for Sonnet. Haiku built `/tmp` virtualenvs with `uv` or `pip`
  to try backends the image leaves out (ibis, pyspark, plus `jdk4py` and `ruff`).
  - These packages were not covered by the #39 audit.
  - They run in a container that also holds the credential.
  - The installs also account for much of Haiku's wall time.
  - This has to be settled before the full run.
- **No high-churn steps or regressions.** Step 1 can't produce regressions. `summary`
  reports rule 1 as firing, but with one step-attempt per arm that means nothing.

## Limits

- `pip-audit` covers Python packages only. The Debian packages in the base image
  are not scanned. They come from the official image, pinned by digest.
- The audit reflects advisories known on 2026-11-07. Rerun `scan.sh` if the full run
  starts much later.
- The model sessions need a credential inside the agent container. It is passed by
  environment variable name only, so it never appears in a command line or a log.
  The container can still read it, and it has network access during model sessions.
