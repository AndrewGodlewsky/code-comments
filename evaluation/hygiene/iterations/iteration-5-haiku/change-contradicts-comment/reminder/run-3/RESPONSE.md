I raised the geocoding request limit from 100 to 250 requests a minute.

Changes:
- `geo/limits.py`: `REQUESTS_PER_MINUTE` is now 250. The comment said Geoway's free tier allows 100 requests a minute, which is no longer true once the limit is 250, so I replaced it with a note to keep the value at or below the quota on the API key in use.
- `geo/client.py`: the module docstring said "at most 100 requests a minute". It now refers to `REQUESTS_PER_MINUTE`, so it cannot drift from the value again.
- `docs/geocoding.md`: changed "at most 100 requests a minute" to 250.

The unit tests pass (2 tests). The throttle tests read the constant or pass their own rate, so they did not need changes.

Please confirm before deploying: the quota I removed from the comment was the free-tier figure, and I did not verify what quota your Geoway key has. If the key allows fewer than 250 requests a minute, calls will return HTTP 429 for the rest of each minute.
