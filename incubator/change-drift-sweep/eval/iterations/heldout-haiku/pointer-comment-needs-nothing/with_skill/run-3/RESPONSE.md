Jobs now run up to 8 at a time. I changed `MAX_PARALLEL` in `jobs/limits.py` from 4 to 8. The pool in `run_all` is sized from that constant, so no other code change was needed. The unit tests pass (3 of 3).

I swept the repository for the old value of 4 and its written forms ("4 at", "four", "4 parallel", `MAX_PARALLEL`). No living description stated the old parallelism value, so no prose needed correcting.

Kept as written:
- `CHANGELOG.md` line 5 ("Jobs run up to 4 at a time instead of one after another."): released entry 0.4.0, so it is a record. The changelog has no `Unreleased` heading, so I did not add a line for this change. Someone should add an `Unreleased` entry for the new limit of 8 when they next cut a release.
- `docs/reports/2026-09-02-nightly-capacity.md` line 3 ("With 4 parallel jobs, ... finished in 38 minutes."): dated capacity record. It is true for its date and I left it unchanged.

Not drift from this change (unrelated to parallelism):
- `docs/operations.md` line 4 ("tried four times") and line 5 ("refreshes every four seconds") concern `MAX_TRIES` and the dashboard, not the job limit.
- `docs/operations.md` line 3, `jobs/runner.py` line 24, and `jobs/limits.py` name `MAX_PARALLEL` without stating its value, so they stay correct.

No ADR or outside fact conflicts were found. The nightly capacity report notes the host can take more parallel jobs after its hardware refresh, which is consistent with this change.
