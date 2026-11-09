I raised the geocoding request limit from 100 to 250 requests a minute. The two unit tests pass.

Changed:
- `geo/limits.py`: `REQUESTS_PER_MINUTE = 250`
- `geo/client.py`: the module docstring now says 250.
- `docs/geocoding.md`: now says 250.

Conflict you need to check: the comment in `geo/limits.py` says Geoway's free tier allows 100 requests a minute per API key, and that going over returns HTTP 429 for the rest of that minute. I left that quota statement as written, because it describes Geoway, not this code. At 250 a minute the client will exceed that quota unless your Geoway plan allows more than the free tier. Please confirm the plan's limit, or raise it with Geoway, before relying on this change in production. If the plan does allow 250, the comment in `geo/limits.py` should be updated to name the plan.

Not changed: the reason for choosing 250 is not recorded anywhere in the repository. I did not add one. If there is a reason, such as a Geoway plan or an agreed throughput target, please tell me so I can record it beside the constant.

Nothing was committed.
