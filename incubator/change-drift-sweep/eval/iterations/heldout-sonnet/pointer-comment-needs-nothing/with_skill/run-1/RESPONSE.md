Done: `MAX_PARALLEL` in `jobs/limits.py` is now 8 (was 4). `run_all` sizes its pool from it, so up to 8 jobs run in parallel. The tests pass.

I swept the comments, docstrings and Markdown docs for the old value, as "4" and "four" and as a total or per-unit figure. Nothing needed correcting:

- `jobs/limits.py`, `jobs/runner.py` and `docs/operations.md` refer to `MAX_PARALLEL` by name without stating its value, so they are already true. I left them as they were.
- `CHANGELOG.md` (0.4.0, "up to 4 at a time"): a released entry, true for that version. I kept it word for word. I did not add an entry because the file has no `Unreleased` heading. Say if you want one.
- `docs/reports/2026-09-02-nightly-capacity.md` ("With 4 parallel jobs..."): a dated measurement, true for the day it was taken. I kept it. It already notes the host can take more parallel jobs.
- "tried four times" (`docs/operations.md`) and "every four seconds" (same file) are unrelated. The first is `MAX_TRIES`, the second is the dashboard refresh.

No instruction-file lines or outside facts are affected, and I found no drift that predates this change.
