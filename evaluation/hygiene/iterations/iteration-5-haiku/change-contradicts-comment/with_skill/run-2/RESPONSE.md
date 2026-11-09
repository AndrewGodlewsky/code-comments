The geocoding request limit is now 250 a minute, up from 100.

Changed files (uncommitted):
- `geo/limits.py`: `REQUESTS_PER_MINUTE = 250`.
- `geo/client.py`: the module docstring now says at most 250 requests a minute.
- `docs/geocoding.md`: now says at most 250 requests a minute.

The unit tests pass (2 of 2).

Please check this before deploying. The comment in `geo/limits.py` says Geoway's free tier allows 100 requests a minute per API key, and that going over returns HTTP 429 for the rest of that minute. I left that vendor statement as written, because it describes Geoway, not this code. At 250 a minute the client will exceed that quota unless your Geoway plan or key allows more. If it does not, the extra calls will fail with 429s and throughput may not improve. Can you confirm the quota on the key this client uses? If you have a higher-tier quota, the `limits.py` comment should be updated to match.

The change is not committed.
