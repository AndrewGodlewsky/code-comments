I changed the retry cap from three to five. `MAX_RETRIES` in `fetcher/config.py` is now 5, so `fetch_report()` makes at most six attempts.

The longer cap also changes the total wait before giving up. The waits are now 2, 4, 8, 16 and 32 seconds, which is 62 seconds, up from 14. I updated every statement of the old behaviour:
- the module docstring in `fetcher/client.py` (five retries, at most six attempts)
- the backoff comment in `fetch_report()` (62 seconds in all)
- `docs/operations.md` (five retries, about 62 seconds)

The test uses `MAX_RETRIES`, so it needed no change. I did not run it.

You didn't give a reason for the change, so I recorded only the new value. If there's a reason, such as a reports-service constraint, tell me and I'll add it beside the constant. Also check that nothing else relies on the old 14-second ceiling, such as the nightly job's timeout. Nothing in this repository does.
