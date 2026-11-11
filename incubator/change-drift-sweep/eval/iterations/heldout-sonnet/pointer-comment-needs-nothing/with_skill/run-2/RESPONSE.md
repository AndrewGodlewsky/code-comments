`MAX_PARALLEL` in `jobs/limits.py` is now 8 (was 4). The runner sizes its thread pool from it, so up to 8 jobs now run at once. The tests pass.

I searched all the prose for the old cap (4, "four", "at a time", "parallel") and found nothing that needed correcting:

- Left alone because they point to the constant without stating its value:
  - the `limits.py` comment
  - the `run_all` docstring
  - the pool comment in `runner.py`
  - `docs/operations.md`, which says the runner never exceeds `MAX_PARALLEL`
- Kept word for word because they are records:
  - `CHANGELOG.md` 0.4.0, "Jobs run up to 4 at a time", is a released entry and was true then. There is no `Unreleased` heading, so I added no changelog line.
  - `docs/reports/2026-09-02-nightly-capacity.md`, "With 4 parallel jobs, ... 38 minutes", is a dated measurement. Its 38-minute figure and 61% CPU peak were measured at 4 and won't hold at 8.
- Unrelated: the 4 tries per job (`MAX_TRIES`, `docs/operations.md`, CHANGELOG 0.3.0) and the dashboard's 4-second refresh. They share the number but describe other things.

No outside facts or instruction-file lines were affected. I found no drift that predates this change.
