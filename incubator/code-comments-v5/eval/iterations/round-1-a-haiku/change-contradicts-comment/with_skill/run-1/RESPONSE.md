I raised the geocoding request limit to 250 a minute.

Changes:
- `geo/limits.py`: `REQUESTS_PER_MINUTE` is now 250. The comment no longer says to keep the value at or below the quota, because that is now false. It keeps Geoway's free-tier quota of 100 a minute as written and states that 250 needs a plan that allows it.
- `geo/client.py`: the module docstring now points to `REQUESTS_PER_MINUTE` instead of repeating the old number of 100.
- `docs/geocoding.md`: the rate now reads 250 a minute.

Conflict to check: Geoway's free tier allows 100 requests a minute per API key, and going over returns HTTP 429 for the rest of that minute. At 250 a minute, this client will get 429s unless the API key is on a plan with a quota of at least 250 a minute. Please confirm the key's plan before deploying. If it is on the free tier, the client needs a different approach, such as a lower limit or a plan upgrade.

Tests: `tests/test_client.py` reads the constant and uses an explicit `per_minute=60` for the wait test, so it needed no change. I did not run the tests.
