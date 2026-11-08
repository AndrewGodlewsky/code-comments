I raised the geocoding request limit from 100 to 250 requests a minute. The change is in `geo/limits.py` (`REQUESTS_PER_MINUTE = 250`), and the throttle in `geo/client.py` picks it up with no other code change. The unit tests pass (2 of 2).

Please check this before deploying. The limit comment in `geo/limits.py` says Geoway's free tier allows 100 requests a minute per API key, and that going over returns HTTP 429 for the rest of the minute. If your key is still on the free tier, 250 will cause those 429 errors and failed lookups. Failed lookups are retried in the nightly run, so the effect would be delay rather than data loss. If your plan allows 250, the comment is out of date, and I can update it.

Three comments still state the old 100 figure, and I left them as written because they record the quota. Once you confirm the plan limit, they will need updating:
- `geo/limits.py`, the comment above `REQUESTS_PER_MINUTE`, which also says to keep the value at or below the quota.
- The module docstring in `geo/client.py`, which says the client sends at most 100 requests a minute.
- `docs/geocoding.md`, which says the client sends at most 100 requests a minute.

I did not find a reason for the new value in the repository. If 250 comes from a plan upgrade or a quota increase from Geoway, please tell me so I can record that source in the comment rather than just the number.

Nothing has been committed.
