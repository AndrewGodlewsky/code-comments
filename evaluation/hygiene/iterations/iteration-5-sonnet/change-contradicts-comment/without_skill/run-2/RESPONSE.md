I raised the geocoding limit from 100 to 250 requests a minute. Check your Geoway quota before you deploy it.

The comment in `geo/limits.py` said the old value of 100 matched Geoway's free-tier quota, and that going over it returns HTTP 429 for the rest of the minute. If your API key is still on the free tier, 250 a minute will hit those errors and throughput will get worse. I couldn't check which plan the key is on. Please confirm it allows at least 250 a minute, or upgrade it, before this goes live. If it doesn't, set the value back to the plan's quota.

What changed:
- `geo/limits.py`: `REQUESTS_PER_MINUTE` is now 250. I rewrote the comment to say the value needs a plan with at least that quota.
- `geo/client.py`: the module docstring now says 250.
- `docs/geocoding.md`: the text now says 250.

I didn't run the tests. `test_interval_matches_limit` reads the constant, so it should pass with the new value.
