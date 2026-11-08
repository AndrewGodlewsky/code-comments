I raised the geocoding request limit from 100 to 250 requests a minute.

Changes:
- `geo/limits.py`: `REQUESTS_PER_MINUTE` is now 250. The comment no longer says the free tier allows 100 as if that were the limit in use. It now says the free tier allows only 100, so this value assumes a plan with at least 250.
- `geo/client.py`: the module docstring pointed at the old hard-coded 100. It now refers to the limit in `geo/limits.py` instead of repeating the number.
- `docs/geocoding.md`: now says 250 requests a minute.

The throttle tests pass (2 tests, OK). They check the interval against the constant, so they do not prove the live API accepts 250.

Please confirm before this ships: the comment in `geo/limits.py` records that Geoway's free tier allows 100 requests a minute per key. Going over returns HTTP 429 for the rest of the minute. I could not verify your current Geoway plan, so I have not confirmed that your key's quota is 250. If the key is still on the free tier, requests will start failing with 429s. Please confirm the quota on your Geoway account, or tell me the correct figure, and I will update the constant and comment to match.
