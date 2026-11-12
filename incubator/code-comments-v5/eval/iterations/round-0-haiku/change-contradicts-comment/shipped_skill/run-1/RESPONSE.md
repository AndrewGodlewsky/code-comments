The request limit is now 250 requests a minute.

Changed:
- `geo/limits.py`: `REQUESTS_PER_MINUTE` is 250.
- `geo/client.py`: the module docstring now says at most 250 requests a minute.
- `docs/geocoding.md`: now says at most 250 requests a minute.

Left as written:
- `geo/limits.py` still says Geoway's free tier allows 100 requests a minute per API key, and that going over returns HTTP 429 for the rest of that minute. That is the vendor fact, so I did not change it.
- The same comment also says "keep this at or below the quota." 250 is above the 100 free-tier quota, so that instruction now conflicts with the new value.

Needs your decision:
- If the account is still on the free tier, 250 will get HTTP 429 responses for the rest of each minute. Confirm the plan or quota Geoway gives this key before shipping. If you are on a higher tier, update the quota note in `geo/limits.py` to say so.
- I did not run the tests. `tests/test_client.py` reads the limit from the constant, so it should still pass.
- No `Throttle` behaviour changed. Calls are now spaced 0.24 seconds apart instead of 0.6.
