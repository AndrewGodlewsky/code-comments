I raised the geocoding request limit from 100 to 250 requests a minute.

Changes:
- `geo/limits.py`: `REQUESTS_PER_MINUTE` is now 250. The comment previously said the free tier allows 100 a minute, which would be false at 250, so I rewrote it. It now says the value must stay within the key's quota and that 250 needs a plan with that quota.
- `geo/client.py`: the module docstring referred to 100 requests a minute. It now points to `REQUESTS_PER_MINUTE` in `geo.limits` instead of hard-coding a number.
- `docs/geocoding.md`: now says 250 requests a minute and notes that the limit lives in `geo/limits.py`.

The unit tests pass (2 of 2). They read the constant rather than a fixed number, so they still hold.

One thing to confirm before this goes live: the old comment says Geoway's free tier allows 100 requests a minute per key, and going over returns HTTP 429 for the rest of that minute. If the key is on the free tier, 250 will produce 429s and failed lookups. Check that the key's plan has a 250-per-minute quota. I could not verify that from this repository.
