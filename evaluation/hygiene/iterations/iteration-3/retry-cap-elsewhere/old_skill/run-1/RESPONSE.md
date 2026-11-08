The retry cap is now five instead of three. `MAX_RETRIES` in `fetcher/config.py` changed from 3 to 5, so `fetch_report()` makes up to six attempts and then raises `ReportUnavailable`. The retry loop itself needed no change.

I also updated the three places that described the old behaviour:
- `fetcher/client.py`: the module docstring now says five retries and six attempts.
- `fetcher/client.py`: the wait comment now lists 2, 4, 8, 16 and 32 seconds, 62 seconds in all (it was 14).
- `docs/operations.md`: it now says five retries and about 62 seconds before a report is given up on (it was three and about 14).

The unit tests pass (`tests/test_client.py`, 2 tests). The test checks the cap through `MAX_RETRIES`, so it adjusts on its own.

Two things to check:
- The change adds about 48 seconds per failing report (62 seconds against 14). If the nightly job has a time budget, that is worth confirming with the reports team.
- The request gave no reason for five retries, so I did not add a rationale comment. If you can tell me why, I will record it next to `MAX_RETRIES` in `fetcher/config.py`.

Nothing is committed.
