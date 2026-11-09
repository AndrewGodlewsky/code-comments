The fetcher now retries five times instead of three before raising `ReportUnavailable`.

What changed (all uncommitted):
- `fetcher/config.py`: `MAX_RETRIES` is 5 (was 3).
- `fetcher/client.py`: the module docstring now says five retries and at most six attempts. The inline comment on the waits now reads 2, 4, 8, 16 and 32 seconds, 62 seconds in all (was 14).
- `docs/operations.md`: five retries, giving up after about 62 seconds (was three and 14).

Verification: the existing unit tests pass (2 of 2). The retry-cap test reads `MAX_RETRIES`, so it now checks six attempts.

Two things to check:
- Nothing in the repo records why the reports team wants five retries, so I did not add a rationale comment. If you want one beside `MAX_RETRIES`, tell me the reason.
- The change makes a worst-case wait of about 62 seconds per report instead of 14. Nightly runs will take longer when the service is down. I did not change the timeout or backoff settings.
