The geocoding request limit is now 250 a minute, up from 100.

Changes:
- `geo/limits.py`: `REQUESTS_PER_MINUTE` is now 250. The comment said 100 was Geoway's free-tier quota and that going over returns HTTP 429, so it would have been false at 250. It now says the value must stay within the quota of the plan the API key is on, and that the free tier allows 100.
- `geo/client.py`: the module docstring said "100 requests"; it now refers to `REQUESTS_PER_MINUTE` so it cannot go stale again.
- `docs/geocoding.md`: states 250 a minute and notes that this needs a plan with at least that quota.

The unit tests pass (`python -m unittest discover -s tests -t .`, 2 tests).

Please check one thing before deploying: I went only by the comment in the code, which says the free tier allows 100 a minute per key. If the key is on the free tier, 250 will return HTTP 429 for the rest of each minute. Confirm that the Geoway plan behind this key has a quota of at least 250 a minute. I could not check that from here.
