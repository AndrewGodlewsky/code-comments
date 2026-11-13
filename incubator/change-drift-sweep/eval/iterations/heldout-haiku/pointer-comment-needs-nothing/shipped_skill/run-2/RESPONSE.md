I raised the parallel job limit from 4 to 8. The only change is `MAX_PARALLEL = 8` in `jobs/limits.py`. `run_all` sizes its thread pool from that constant, so the new cap takes effect without other edits. The existing unit tests pass (3 tests, OK).

I checked the comments that touch this value and left them as they are:
- The comment above `MAX_PARALLEL` names no number, so it stays true.
- `docs/operations.md` refers to the constant, not its value, so it stays true.
- `CHANGELOG.md` records the 0.4.0 change ("up to 4 at a time"). That is a dated history entry, so I did not change it. I did not add an entry for this change. Say if you want a new version entry.
- `docs/reports/2026-09-02-nightly-capacity.md` is a dated capacity report from before the hardware refresh, so it stays as written.
