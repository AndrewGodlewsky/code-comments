The runner now allows up to 8 jobs to run in parallel, up from 4.

What changed:
- `jobs/limits.py`: `MAX_PARALLEL` is now `8`. `run_all` sizes its thread pool from this constant, so the cap follows it with no other code change.
- `CHANGELOG.md`: added an Unreleased entry noting the new limit.

Verification: `python -m unittest` runs 3 tests, all passing. The concurrency test checks that the peak never exceeds `MAX_PARALLEL`, so it now checks against 8.

`docs/operations.md` refers to the constant by name rather than by number, so it needs no edit. Nothing was committed.
