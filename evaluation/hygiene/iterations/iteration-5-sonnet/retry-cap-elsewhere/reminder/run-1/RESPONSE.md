The fetcher now retries five times instead of three, so a report gets up to six attempts before `ReportUnavailable` is raised.

- `fetcher/config.py`: `MAX_RETRIES` changed from 3 to 5.
- Comments and docs that the change made false are updated:
  - The module docstring in `fetcher/client.py` now says five retries and at most six attempts.
  - The backoff comment in `fetcher/client.py` now lists waits of 2, 4, 8, 16 and 32 seconds, 62 seconds in all.
  - `docs/operations.md` now says five retries and about 62 seconds.

The total wait before giving up grows from 14 to 62 seconds. That slows the nightly job whenever the reports service is down, so tell the reports team if that matters.

I did not run the tests. The existing test uses `MAX_RETRIES`, so it needs no change.
