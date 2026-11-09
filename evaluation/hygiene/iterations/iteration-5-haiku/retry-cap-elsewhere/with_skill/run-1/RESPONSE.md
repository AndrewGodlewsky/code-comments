The reports fetcher now retries five times instead of three before raising `ReportUnavailable`. A caller makes six attempts in total, and the waits double from 2 seconds (2, 4, 8, 16, 32), so a report gives up after about 62 seconds rather than 14.

Changes:
- `fetcher/config.py`: `MAX_RETRIES` is now 5.
- `fetcher/client.py`: the module docstring and the timing comment now describe five retries, six attempts and 62 seconds.
- `docs/operations.md`: the operator note now says five retries and about 62 seconds.

The existing unit tests pass (`python -m unittest discover -s tests -t .`). The retry-cap test reads `MAX_RETRIES`, so it checks the new count without changes.

Nothing is committed. The change is in the working tree only.

One thing to check: the nightly job's timeout or scheduling may assume the old 14-second window, and I did not look for that outside this repository.
