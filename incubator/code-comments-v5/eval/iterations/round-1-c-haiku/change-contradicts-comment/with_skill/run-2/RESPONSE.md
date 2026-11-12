I raised the geocoding request limit to 250 requests a minute.

Changes:
- `geo/limits.py`: `REQUESTS_PER_MINUTE` is now 250. The comment still states Geoway's free tier quota (100 a minute per API key, HTTP 429 when exceeded). It no longer says to stay at or below the quota. It now says the value assumes the API key is on a plan that allows 250 a minute.
- `geo/client.py`: the module docstring now says the client sends at most 250 requests a minute.
- `docs/geocoding.md`: now says the client sends at most 250 requests a minute.

Tests: `python -m unittest tests.test_client` passes (2 tests). The throttle reads the constant, so no test changes were needed.

Conflict to check before merging:
- Geoway's documented free tier allows 100 requests a minute per API key. At 250, calls beyond 100 in a minute will get HTTP 429 unless the key is on a plan with a 250-a-minute quota. The code does not record which plan the key is on, so I could not verify that. Please confirm the account's quota with Geoway. If the key is still on the free tier, the throughput gain will not happen and the client will receive 429s for the rest of each minute.
- I left the vendor quota statement as written, because it describes Geoway, not this code.

Missing information: nothing in the repository or the request says which plan the key has. I did not add a plan name or ticket reference to the comment for that reason. If you have a ticket or plan name for the 250 quota, it should go beside the constant in `geo/limits.py`.
