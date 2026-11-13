Raised the parallel job cap from 4 to 8.

Changed: `MAX_PARALLEL = 4` to `MAX_PARALLEL = 8` in `jobs/limits.py`. `run_all` sizes its thread pool from this value and the concurrency test reads it symbolically, so no other code changed. `python -m unittest` passes (3 tests).

Checked and left alone:
- `docs/operations.md` names `MAX_PARALLEL` without a figure, so it is still accurate.
- `README.md`, `jobs/runner.py` and `tests/test_runner.py` contain no figure for the cap.
- `CHANGELOG.md` 0.4.0 says "up to 4 at a time". That is a historical entry and I left it as written. If you want the change recorded, add a new entry for 8.
- `docs/reports/2026-09-02-nightly-capacity.md` says "With 4 parallel jobs ... 38 minutes". It is a dated report and I left it as written. Its figures describe the 4-job run only.

Mismatches not caused by this change: none found. `MAX_TRIES = 4` and "tried four times" in `docs/operations.md` describe retries, not parallelism, and are unchanged.
