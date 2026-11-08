The report fetcher now retries five times instead of three before raising `ReportUnavailable`.

Changes:
- `fetcher/config.py`: `MAX_RETRIES` changed from 3 to 5. The test reads this constant, so it now checks for six attempts.
- `fetcher/client.py`: the module docstring and the backoff comment now describe five retries, six attempts, and waits of 2, 4, 8, 16 and 32 seconds (62 seconds in all).
- `docs/operations.md`: the operations note now says five retries and about 62 seconds before a report is given up on.

The unit tests pass (2 tests). I did not run against the live reports service.
