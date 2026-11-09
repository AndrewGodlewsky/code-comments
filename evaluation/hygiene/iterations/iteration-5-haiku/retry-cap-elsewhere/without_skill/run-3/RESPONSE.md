The fetcher now retries five times instead of three before it gives up on a report.

What changed:
- `fetcher/config.py`: `MAX_RETRIES` is now 5. With the 2-second starting backoff, the waits are 2, 4, 8, 16 and 32 seconds, so a report gives up after about 62 seconds (it was about 14 seconds before).
- `fetcher/client.py`: the module docstring and the inline comment now describe five retries, six total attempts, and the 62-second total.
- `docs/operations.md`: the operator guide now says five retries and about 62 seconds.

The retry loop in `fetch_report()` already reads `MAX_RETRIES`, so no logic changed. The existing test in `tests/test_client.py` checks against `MAX_RETRIES`, and it passes (2 tests, OK).

Note for the reports team: the nightly job will now wait about 62 seconds on each report that keeps timing out, instead of about 14 seconds. If a night has many failing reports, the run will take noticeably longer.

Nothing was committed.
