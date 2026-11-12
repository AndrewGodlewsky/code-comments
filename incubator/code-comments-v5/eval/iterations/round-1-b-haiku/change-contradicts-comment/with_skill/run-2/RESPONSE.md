I raised the geocoding request limit to 250 requests a minute.

Changes:
- `geo/limits.py`: `REQUESTS_PER_MINUTE` is now 250.
- `geo/client.py`: the module docstring now says the client sends at most 250 requests a minute.
- `docs/geocoding.md`: now says at most 250 requests a minute.

The unit tests in `tests/test_client.py` pass (2 of 2). They read the limit from the constant, so they needed no change.

Conflict you need to check: the comment in `geo/limits.py` says Geoway's free tier allows 100 requests a minute per API key, and that going over returns HTTP 429 for the rest of the minute. It also says to keep the value at or below the quota. At 250 the client will exceed that free-tier quota unless your API key is on a plan with a higher limit. I left the quota statement as written, because it describes the vendor's limit, and I did not rewrite it to fit the change. If you are on a higher tier, that comment should be updated to name the tier. If you are not, the 250 setting will cause 429 errors.

I did not add a rationale for the increase, because none was given in the request. If you have a ticket or reason for it, tell me and I will record it beside the constant.
