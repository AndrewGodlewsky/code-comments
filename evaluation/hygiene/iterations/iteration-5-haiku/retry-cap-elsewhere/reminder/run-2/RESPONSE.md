The retry cap is now five instead of three. `MAX_RETRIES` in `fetcher/config.py` is set to 5, so `fetch_report()` makes up to six attempts (one initial call plus five retries) before it raises `ReportUnavailable`.

The change also made four comments and docs false, and I updated them:
- `fetcher/client.py` module docstring: now says five retries and at most six attempts.
- `fetcher/client.py` inline comment: the backoff waits are now 2, 4, 8, 16 and 32 seconds, 62 seconds in total, not 14.
- `docs/operations.md`: now says the fetcher retries five times and gives up after about 62 seconds.

The existing unit tests read `MAX_RETRIES`, so they still pass (2 tests, OK). I did not run the code against the real reports service.

Note that a report that keeps timing out now holds the nightly job for about a minute before it is skipped, not about 14 seconds. If the job has a time budget, that is worth checking before this goes out.
