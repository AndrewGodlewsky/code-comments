I raised `REQUESTS_PER_MINUTE` in `geo/limits.py` from 100 to 250.

Conflict: the code comment in `geo/limits.py` says Geoway's free tier allows 100 requests a minute per API key, and going over returns HTTP 429 for the rest of that minute. At 250, the client will get 429s unless the API key is on a plan with a quota of at least 250. I kept the vendor quota sentence as written and did not change it to fit the new value. I can't tell from the repo which plan the key is on, so please confirm that before this ships.

Updated to keep the text true:
- `geo/limits.py`: the comment now says the value is above the free-tier quota. The old "keep this at or below the quota" line is gone, since it no longer describes the code.
- `geo/client.py`: the module docstring pointed at "100 requests a minute". It now refers to the limit set in `geo.limits`, so the number lives in one place.
- `docs/geocoding.md`: now says 250 requests a minute, and notes the 100-per-minute free-tier quota and the HTTP 429 behaviour above it.

Callers: `geo.client.Throttle` reads `REQUESTS_PER_MINUTE` as its default, so it now spaces calls every 0.24 s instead of 0.6 s. `tests/test_client.py` compares against the constant, not a literal, so it needed no change. `python -m unittest tests.test_client` passes (2 tests).

Not done: no commit, since git was out of scope for this exercise. No commented-out code was found.

Question: is the Geoway key on a plan with a quota of at least 250 requests a minute? If not, the value should stay at 100 or the key's plan needs to change.
