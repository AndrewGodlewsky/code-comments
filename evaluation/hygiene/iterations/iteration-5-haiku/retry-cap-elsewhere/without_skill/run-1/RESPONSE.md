The fetcher now retries five times instead of three before giving up on a report.

Changes:
- `fetcher/config.py`: `MAX_RETRIES` changed from 3 to 5. This is the value `fetch_report()` reads, so the cap itself is now five retries (six attempts in total).
- `fetcher/client.py`: the module docstring and the inline wait comment were updated. The waits are now 2, 4, 8, 16 and 32 seconds, which is 62 seconds in total before `ReportUnavailable` is raised (it was 14 seconds).
- `docs/operations.md`: updated from three retries and about 14 seconds to five retries and about 62 seconds.

Checks: the existing unit tests pass (`python -m unittest discover -s tests -t .`, 2 tests OK). The retry-cap test reads `MAX_RETRIES`, so it follows the new value without changes.

Please note the longer wait: a report that keeps timing out now holds the nightly job for about 62 seconds per report, up from about 14. Nothing was committed.
