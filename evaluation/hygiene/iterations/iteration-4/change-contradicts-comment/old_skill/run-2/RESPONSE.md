The geocoding request limit is now 250 a minute (was 100).

Changes (uncommitted):
- geo/limits.py: REQUESTS_PER_MINUTE = 250.
- geo/client.py: module docstring now says "at most 250 requests a minute".
- docs/geocoding.md: now says "at most 250 requests a minute".

The unit tests pass (2 of 2).

Conflict you need to decide on: the comment in geo/limits.py says Geoway's free tier allows 100 requests a minute per API key, and that going over returns HTTP 429 for the rest of the minute. The new value of 250 is above that quota. I left the vendor fact as written. If your account is on a plan that allows 250, that comment should be updated to say so. I did not write that in, because I don't know your plan's limit. If you are still on the free tier, expect 429 responses above 100 a minute, and the client will not handle them differently from before.

Also note: the comment in geo/limits.py still says to keep the value at or below the quota. That instruction is now violated by the change, and I did not reword it for the same reason.
