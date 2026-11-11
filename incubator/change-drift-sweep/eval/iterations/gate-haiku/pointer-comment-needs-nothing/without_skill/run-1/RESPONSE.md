Done. The job runner now allows up to 8 jobs in parallel, up from 4.

- `jobs/limits.py`: `MAX_PARALLEL` changed from 4 to 8. `run_all` sizes its thread pool from this value, so the cap applies everywhere with no other code changes.
- `CHANGELOG.md`: added an "Unreleased" entry recording the new limit.

`python -m unittest` passes (3 tests), including the test that checks concurrency never exceeds `MAX_PARALLEL`.

Note: the 2026-09-02 capacity report measured CPU peaking at 61% with 4 jobs. Going to 8 roughly doubles the load, so watch CPU on the first nightly run after this change. The `MAX_TRIES` setting is unchanged.
