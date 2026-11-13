Done: `MAX_PARALLEL` in `jobs/limits.py` is now 8 (was 4). `run_all` sizes its thread pool from it, so up to 8 jobs now run at once.

Comments and docs: nothing needed correcting. The comment in `limits.py`, the docstring and comment in `jobs/runner.py`, and `docs/operations.md` refer to `MAX_PARALLEL` by name and never state the number, so they are still accurate. The test uses `limits.MAX_PARALLEL` too.

Left as written on purpose:
- `CHANGELOG.md` 0.4.0 says "up to 4 at a time". That is a historical entry.
- `docs/reports/2026-09-02-nightly-capacity.md` (4 parallel jobs, 38 minutes) is a dated report.

No mismatches found that my change did not cause. The "4 tries" figures (`MAX_TRIES`, `docs/operations.md`) and the "four seconds" dashboard refresh are separate values and unchanged.

I did not run the tests.
