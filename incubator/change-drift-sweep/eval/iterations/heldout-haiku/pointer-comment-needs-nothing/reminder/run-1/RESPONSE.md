Raised the parallel job cap from 4 to 8.

Changed:
- jobs/limits.py: MAX_PARALLEL = 4 -> MAX_PARALLEL = 8. run_all sizes its thread pool from this constant, so no other code changed.

Checked and left alone:
- docs/operations.md names MAX_PARALLEL but states no figure, so it is still accurate. Its "four times" and "four seconds" refer to MAX_TRIES and the dashboard refresh, not to the cap.
- jobs/runner.py, jobs/__init__.py, README.md and tests/test_runner.py contain no figure for the cap. The tests read limits.MAX_PARALLEL, so they follow the new value.
- CHANGELOG.md (0.4.0 "up to 4 at a time") is a historical entry and was left word for word. A new entry for 8 is not something I added, since the request did not ask for one.
- docs/reports/2026-09-02-nightly-capacity.md is a dated report and was left word for word. It records a run with 4 parallel jobs, which was true on that date.

Mismatches not caused by this change: none found.

Verification: python -m unittest ran 3 tests, all passing.
