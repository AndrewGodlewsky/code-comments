Done. The runner now lets up to 8 jobs run in parallel.

**Change**

- `jobs/limits.py`: `MAX_PARALLEL` goes from 4 to 8. `run_all` sizes its thread pool from this value, so no other code changes are needed. The unit tests pass (3 of 3), including the concurrency-cap test, which now checks against 8.

**Drift sweep**

- Corrected: nothing. No living description in the repo states the parallel limit as a number. `docs/operations.md` refers to `MAX_PARALLEL` by name, which stays true.
- Kept as records:
  - `CHANGELOG.md`, the 0.4.0 entry ("Jobs run up to 4 at a time"), is a released entry describing the 0.4.0 state.
  - `docs/reports/2026-09-02-nightly-capacity.md` ("With 4 parallel jobs ...") is a dated capacity report.
- Unrelated: `docs/operations.md` line 4 says "tried four times", which is the retry count (`MAX_TRIES`). I did not touch it.
- No derived figures depend on the parallel limit.
- The changelog has no `Unreleased` heading, so I did not add a line for this change. If you want one, it would be something like "Jobs run up to 8 at a time." under a new `Unreleased` heading.
