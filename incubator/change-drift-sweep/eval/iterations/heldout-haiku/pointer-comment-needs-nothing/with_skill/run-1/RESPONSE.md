Done. The runner now allows up to 8 jobs in parallel.

- Changed `MAX_PARALLEL` from 4 to 8 in `jobs/limits.py`. `run_all` sizes its thread pool from this constant, so no other code changed.
- Ran the test suite (`python -m unittest`): 3 tests, all pass.
- Swept the repository for the old value 4 and its written forms ("four", "4 at a time"). Nothing living still states the old cap:
  - `CHANGELOG.md` line 5 ("Jobs run up to 4 at a time") is the released 0.4.0 entry, so it is kept as written. The file has no `Unreleased` heading, so I did not add a changelog line for this change. Add one under the next release heading if you want it recorded.
  - `docs/reports/2026-09-02-nightly-capacity.md` ("With 4 parallel jobs") is a dated capacity report, so it is kept as written.
  - `docs/operations.md` names `MAX_PARALLEL` without a value, so it stays true. Its "tried four times" and "every four seconds" refer to `MAX_TRIES` and the dashboard refresh, which are unrelated, so they are left alone.
  - `jobs/runner.py` docstring and the comment in `jobs/limits.py` also name the constant without a value, so they are unchanged.
- No ADRs or instruction files in this repository are affected.
