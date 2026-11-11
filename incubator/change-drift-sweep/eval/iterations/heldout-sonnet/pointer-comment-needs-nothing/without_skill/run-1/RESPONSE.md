The runner now allows up to 8 jobs in parallel. I changed `MAX_PARALLEL` from 4 to 8 in `jobs/limits.py`. The thread pool in `run_all` reads that constant, so nothing else in the code needed to change. The 3 existing tests pass.

I also added an "Unreleased" entry to `CHANGELOG.md` saying jobs now run up to 8 at a time. I left the earlier 0.4.0 entry alone, since it records what that release did.

I left these 4s alone because they are unrelated to parallelism: the 4 tries per failing job (`MAX_TRIES`), and the 4-second dashboard refresh in `docs/operations.md`.

`docs/operations.md` and the comments in `limits.py` and `runner.py` refer to `MAX_PARALLEL` by name, not by number, so they are still correct. I did not touch the 2026-09-02 capacity report, which records the 4-job run.

I didn't load-test 8 workers on the refreshed host. The capacity report only measured 4.
