I raised `REQUESTS_PER_MINUTE` to 250 in `geo/limits.py`. I also updated the two places that describe the client's behaviour, the module docstring in `geo/client.py` and `docs/geocoding.md`, so they now say 250 a minute. The tests pass.

**This conflicts with the Geoway quota.** The comment in `geo/limits.py` says Geoway's free tier allows 100 requests a minute per API key, and that going over returns HTTP 429 for the rest of that minute. I left that comment as written, because it is a fact about Geoway and not about our code. At 250 a minute the client will exceed the free-tier quota unless we are on a higher plan or key. Expect 429s otherwise.

Can you confirm which plan or quota we have? If it really is higher than 100, send me the figure and I will update the comment. I did not record a reason for the new value, because none was given. Tell me if you want one noted.
