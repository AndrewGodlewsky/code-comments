The runner now allows up to 8 jobs in parallel. I changed `MAX_PARALLEL` in `jobs/limits.py` from 4 to 8. `run_all` sizes its thread pool from that constant, so no other code needed to change.

Checked for stale references to the old value:
- `docs/operations.md` and the `run_all` docstring name `MAX_PARALLEL` rather than a number, so they already describe the new behaviour. No change.
- `tests/test_runner.py` derives its expectations from `MAX_PARALLEL`, so it adapts. No change.
- `CHANGELOG.md` 0.4.0 says "up to 4 at a time". That is a historical changelog entry, so I left it word for word. A new changelog entry for the 8-job limit would be the place to record this change, if you want one.
- `docs/reports/2026-09-02-nightly-capacity.md` says "With 4 parallel jobs..." and is dated, so I left it word for word. Its statement that the host can take more jobs after the hardware refresh is consistent with this change.

Mismatches not caused by this change: none found. The "tried four times" wording in `docs/operations.md` and the 0.3.0 changelog entry match `MAX_TRIES = 4`, and the unrelated "refreshes every four seconds" line in `docs/operations.md` has no counterpart in the code I read.
