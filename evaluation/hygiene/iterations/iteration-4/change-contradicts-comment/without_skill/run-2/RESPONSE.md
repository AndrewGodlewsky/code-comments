I raised the geocoding request limit from 100 to 250 requests a minute. The client now spaces calls about 0.24 seconds apart. The two unit tests pass.

Changed files:
- `geo/limits.py`: `REQUESTS_PER_MINUTE = 250`, with the quota comment updated.
- `geo/client.py`: the module docstring now says 250.
- `docs/geocoding.md`: now says 250.

Before this goes to production, please check one thing. The code comment said Geoway's free tier allows 100 requests a minute per API key, and going over returns HTTP 429 for the rest of that minute. If the key is still on the free tier, 250 will produce a stream of 429 errors. Failed lookups are retried in the nightly run, so they would not be lost, but the throughput gain would not happen. Please confirm the key's plan allows 250 a minute before deploying.

I did not commit anything.
