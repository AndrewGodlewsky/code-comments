The fetcher now retries five times instead of three before raising `ReportUnavailable`, so a report gets six attempts in total.

What changed:
- `fetcher/config.py`: `MAX_RETRIES` is now 5. The retry loop in `fetcher/client.py` reads this constant, so no logic changed.
- `fetcher/client.py`: updated the module docstring (five retries, six attempts) and the backoff comment. The waits are now 2, 4, 8, 16 and 32 seconds, which is 62 seconds in all, up from 14.
- `docs/operations.md`: updated the retry count and the failure window (about 62 seconds).

Checks: the existing unit tests pass (2 tests). They read `MAX_RETRIES`, so they now assert six calls.

One thing to be aware of: the total wait before a report is given up on goes from about 14 seconds to about 62 seconds. If the nightly job has a time budget, that is worth confirming with the reports team.
