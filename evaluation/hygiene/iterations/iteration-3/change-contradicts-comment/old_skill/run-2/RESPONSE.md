I raised the geocoding request limit from 100 to 250 a minute. The two unit tests pass.

Changed:
- `geo/limits.py`: `REQUESTS_PER_MINUTE` is now 250.
- `geo/client.py`: the module docstring now says the client sends at most 250 requests a minute.
- `docs/geocoding.md`: now says 250 a minute.

Conflict you need to check before this ships: the comment in `geo/limits.py` says Geoway's free tier allows 100 requests a minute per API key, and that going over returns HTTP 429 for the rest of the minute. I left that note unchanged, because it is a stated fact about the quota and not something my change should rewrite. If your key is still on the free tier, calls above 100 a minute will start failing with 429s, and failed lookups are retried only in the nightly run. Please confirm that your Geoway plan allows 250 a minute. If it does, the quota note is out of date and should be updated by whoever knows the current plan. I did not verify the plan.

Nothing is committed.
