The geocoding request limit is now 250 a minute, changed in `geo/limits.py`. The client's throttle reads this value, so it now spaces calls at 240 ms apart. The client docstring in `geo/client.py` and `docs/geocoding.md` now say 250. The two unit tests pass.

Please check one thing before this ships. The comment in `geo/limits.py` says Geoway's free tier allows 100 requests a minute per API key, and that going over returns HTTP 429 for the rest of that minute. I kept that vendor fact as written. I rewrote the sentence that told you to keep the value at or below the quota, and it now says calls beyond 100 a minute may be rejected. If your key is on the free tier, expect 429 errors above 100 a minute. If your plan allows 250, the vendor fact in that comment is out of date and should be corrected.

I did not commit anything.
