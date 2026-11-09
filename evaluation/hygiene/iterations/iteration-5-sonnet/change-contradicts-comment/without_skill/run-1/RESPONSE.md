I raised the geocoding request limit from 100 to 250 a minute. The `Throttle` now spaces calls 0.24 seconds apart instead of 0.6. I didn't run the tests.

**Check the quota before deploying.** The comment in `geo/limits.py` said 100 a minute is Geoway's free-tier quota per API key, and that going over returns HTTP 429 for the rest of that minute. I can't see which plan your key is on. If it's still the free tier, 250 a minute will hit 429s and could lower throughput. You'll need a plan that allows at least 250 a minute first. If you have one, no further code change is needed.

What changed:
- `geo/limits.py`: `REQUESTS_PER_MINUTE` is now 250, and I rewrote the comment so it says the limit must stay at or below the plan's quota.
- `geo/client.py` and `docs/geocoding.md`: the text saying "at most 100 requests a minute" now says 250.

The existing test uses the constant, so it needed no change.
