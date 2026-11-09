I have not changed the limit to 250 yet. The code and docs say Geoway's free tier allows 100 requests a minute per API key, and going over returns HTTP 429 for the rest of that minute. `geo/limits.py` says to keep the limit at or below the quota, and `docs/geocoding.md` says the client sends at most 100 requests a minute.

Can you confirm which Geoway plan the key is on and that its quota is 250 a minute? If it is, I will set `REQUESTS_PER_MINUTE = 250` in `geo/limits.py` and update the comment there, the module docstring in `geo/client.py`, and the sentence in `docs/geocoding.md`. If the key is on the free tier, 250 would send about 150 requests a minute over the quota, and the extra calls would fail with 429. Failed lookups are retried in the nightly run, so that would slow the run rather than lose addresses.

Nothing in the repository has been modified.
