Done. The job runner now allows up to 8 jobs in parallel.

I changed `MAX_PARALLEL` in `jobs/limits.py` from 4 to 8. `run_all` sizes its thread pool from that constant, so no other code needed to change. The unit tests pass (`python -m unittest`, 3 tests OK). The concurrency test now checks the cap of 8.

I left `docs/operations.md` alone because it refers to the constant by name, not by value. I also left the 0.4.0 entry in `CHANGELOG.md` and the 2 September capacity report as they are, since they record past states. If you want this release noted, add an "Unreleased" entry to `CHANGELOG.md` saying jobs now run up to 8 at a time.
