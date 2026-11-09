I raised the geocoding request limit from 100 to 250 requests a minute.

Changes:
- `geo/limits.py`: `REQUESTS_PER_MINUTE = 250`.
- `geo/client.py`: the module docstring now refers to `REQUESTS_PER_MINUTE` instead of repeating the number.
- `docs/geocoding.md`: points to `geo/limits.py` for the limit instead of stating 100.

The unit tests pass (2 of 2). The throttle derives its interval from the constant, so spacing is now 60/250 seconds per call.

Conflict to check before deploying: the comment in `geo/limits.py` says Geoway's free tier allows 100 requests a minute per API key, and that going over returns HTTP 429 for the rest of that minute. I left that vendor fact as written, and the comment's "keep this at or below the quota" note is also unchanged. At 250 the client will exceed the free-tier quota if the key is on that tier. Please confirm the account's plan allows 250 a minute. If it does not, the 429s will cause failed lookups, which are logged and retried in the next nightly run.

Missing reason: the change itself has no reason recorded in the code, since none was given beyond needing more throughput. If you have the plan or ticket that authorises 250, it should be cited beside the constant.
