Done. The runner now allows up to 8 jobs in parallel.

- `jobs/limits.py`: `MAX_PARALLEL` changed from 4 to 8. `run_all` sizes its thread pool from this constant, so no other code change was needed.
- `CHANGELOG.md`: added an "Unreleased" entry noting the new limit.

`docs/operations.md` refers to `MAX_PARALLEL` by name rather than by number, so it stays accurate and was not changed. `docs/reports/2026-09-02-nightly-capacity.md` is a dated record of the 4-job run and was left as is.

The existing unit tests pass (3 tests). The concurrency test reads the cap from `MAX_PARALLEL`, so it now checks for up to 8 concurrent jobs. I did not run a load test on the new host.
