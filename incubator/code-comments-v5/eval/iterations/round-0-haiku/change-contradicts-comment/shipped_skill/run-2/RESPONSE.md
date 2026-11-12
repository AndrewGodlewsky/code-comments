I raised the request limit to 250 a minute. `geo/limits.py` now sets `REQUESTS_PER_MINUTE = 250`, and the client throttle picks it up from there.

Conflict to review: the comment in `geo/limits.py` says Geoway's free tier allows 100 requests a minute per API key, and that going over returns HTTP 429 for the rest of that minute. At 250 the client will exceed that quota, so expect HTTP 429 responses once a minute passes 100 requests. I left the quota fact as written, because it describes the vendor, and replaced the old "keep this at or below the quota" advice with a note that this value is above it. If Geoway's quota has changed or you hold a higher-tier key, update that comment to match.

Other changes so the docs match the code:
- `geo/client.py` module docstring: "at most 100 requests a minute" now says 250.
- `docs/geocoding.md`: "at most 100 requests a minute" now says 250.

I did not find a reason in the request or the files for choosing 250 specifically, so the new value is recorded without one.

Tests: `tests/test_client.py` passes (2 tests). Nothing was committed, since this run was limited to the repository files.
