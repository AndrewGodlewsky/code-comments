The geocoding request limit is now 250 a minute, set in `geo/limits.py` (`REQUESTS_PER_MINUTE = 250`). The throttle in `geo/client.py` reads that constant, so it picks up the new value.

I also corrected the three places that stated the old limit of 100:

- `geo/limits.py`: the comment said Geoway's free tier allows 100 a minute. I replaced it with a note that the quota is set by the API key's plan and that going over returns HTTP 429.
- `geo/client.py`: the module docstring now points to `REQUESTS_PER_MINUTE` instead of repeating a number.
- `docs/geocoding.md`: now says 250 and names `geo/limits.py` as the place it is set.

Before this goes live, please confirm that the API key you use has a quota of at least 250 requests a minute. The old comment said the free tier allows 100. If the key's quota is lower, Geoway will return HTTP 429 for the rest of each minute once the client passes that quota. I could not verify the quota for your plan from the repository, so the new comment does not name a source for the 250 figure.

I did not run the test suite. The existing tests read the constant rather than hard-coding 100, so they should still pass.
