The geocoding request limit is now 250 a minute, up from 100.

Changes:
- `geo/limits.py`: `REQUESTS_PER_MINUTE` is now 250. The comment no longer says the free tier allows 100 a minute, because that is no longer the configured value. It now says to keep the limit at or below the Geoway quota for the API key in use.
- `geo/client.py`: the module docstring now says at most 250 requests a minute.
- `docs/geocoding.md`: now says at most 250 requests a minute.

Tests: the two unit tests in `tests/test_client.py` pass.

Please confirm before relying on this: the old comment said Geoway's free tier allows 100 a minute per key. I did not verify the quota for your account. If the key is on the free tier, or its quota is below 250, calls past the quota will get HTTP 429 for the rest of that minute. Check the Geoway quota for the key in use before deploying.
