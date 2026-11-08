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

## Limits

- `pip-audit` covers Python packages only. The Debian packages in the base image
  are not scanned. They come from the official image, pinned by digest.
- The audit reflects advisories known on 2026-11-07. Rerun `scan.sh` if the full run
  starts much later.
- The model sessions (#41) need API credentials inside the container. How they are
  passed is decided in #41, before the smoke run.
