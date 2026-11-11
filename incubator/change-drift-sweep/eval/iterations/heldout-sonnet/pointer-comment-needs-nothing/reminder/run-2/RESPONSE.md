Done: `MAX_PARALLEL` in `jobs/limits.py` is now 8 (was 4). `run_all` sizes its thread pool from it, so up to 8 jobs now run at once.

I checked the comments and docs that mention the limit. The comments in `limits.py` and `runner.py` and `docs/operations.md` refer to `MAX_PARALLEL` by name and state no number, so they are still correct and I left them alone. The tests use the constant too.

Left as is on purpose:
- `CHANGELOG.md` 0.4.0 says "up to 4 at a time". That is a dated release entry.
- `docs/reports/2026-09-02-nightly-capacity.md` records the 4-job run (38 minutes). That is a dated report.

The other 4s are not the parallel cap and did not change. They are `MAX_TRIES = 4` (the changelog and `operations.md` say "tried four times") and the dashboard refresh of "four seconds" in `operations.md`.

I found no mismatches that were not caused by this change. I did not run the tests.
