The job runner now lets up to 8 jobs run in parallel, up from 4.

I changed `MAX_PARALLEL` in `jobs/limits.py` from 4 to 8. `run_all` in `jobs/runner.py` sizes its thread pool from that constant, so the new cap takes effect there with no other code change. `docs/operations.md` refers to the constant by name rather than a number, so it stays accurate. I also added an Unreleased entry to `CHANGELOG.md` noting the change.

I did not run the test suite in this environment.
