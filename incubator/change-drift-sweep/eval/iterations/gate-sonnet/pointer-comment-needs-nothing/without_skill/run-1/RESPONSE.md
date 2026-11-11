The runner now allows up to 8 jobs in parallel. I changed `MAX_PARALLEL` from 4 to 8 in `jobs/limits.py`.

That is the only code change. `run_all` sizes its thread pool from that constant, and the cap test uses it too, so both pick up the new value. The comments and `docs/operations.md` refer to `MAX_PARALLEL` by name rather than by number, so they stay correct. I left the retry count and the dashboard refresh interval at 4, since they are unrelated.

I added an "Unreleased" entry to `CHANGELOG.md` and left the 0.4.0 entry as it was, because it records what that release did. I did not run the tests.

`docs/reports/2026-09-02-nightly-capacity.md` is a dated measurement with 4 jobs, so I left it unchanged. It does not cover how the batch behaves at 8.
