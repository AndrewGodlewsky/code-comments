The retry cap is now five retries instead of three, so `fetch_report()` makes up to six attempts before raising `ReportUnavailable`.

Changes:
- `fetcher/config.py`: `MAX_RETRIES` is now 5.
- `fetcher/client.py`: the module docstring now says five retries and six attempts. The backoff comment now gives the waits as 2, 4, 8, 16 and 32 seconds, 62 seconds in all.
- `docs/operations.md`: the retry count is now five, and the failure window is about 62 seconds instead of 14.

The unit tests pass. The test reads `MAX_RETRIES`, so it needed no change.

I did not record a reason for the change in the code, because none was given beyond the reports team's request. Could you tell me why they want five retries? If there is a reason, I can add it beside `MAX_RETRIES` in `fetcher/config.py`.
