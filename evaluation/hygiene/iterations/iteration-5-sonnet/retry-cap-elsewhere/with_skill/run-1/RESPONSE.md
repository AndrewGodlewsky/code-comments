The fetcher now retries five times instead of three: `MAX_RETRIES` in `fetcher/config.py` is 5, so a report gets at most six attempts before `ReportUnavailable` is raised. The tests pass.

I also updated the statements that described the old behaviour:
- The module docstring in `fetcher/client.py` now says five retries and at most six attempts.
- The backoff comment in `fetch_report` now lists waits of 2, 4, 8, 16 and 32 seconds, 62 seconds in all (it was 14).
- `docs/operations.md` now says five retries and about 62 seconds.

A failing report now holds up the nightly job for about 62 seconds instead of 14. If many reports fail in one night, that adds up. I wasn't given a reason for the change, so I didn't record one in the code. If you have one, such as a reports team request or ticket, tell me and I can add it.
