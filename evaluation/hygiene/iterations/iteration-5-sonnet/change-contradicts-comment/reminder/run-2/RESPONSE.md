I raised `REQUESTS_PER_MINUTE` in `geo/limits.py` from 100 to 250. I did not run the tests.

One thing to check before you deploy: the comment next to that constant said 100 a minute was Geoway's free-tier quota, and that going over it returns HTTP 429 for the rest of the minute. I can't tell from the repo whether the key now in use is on a plan that allows 250 a minute. If it isn't, the client will hit 429s and lose the remainder of each minute, so please confirm the quota first.

Because the old comment named the free tier and a figure of 100, it was no longer true. I reworded it to say the quota is per key and depends on the plan, and I kept the 429 warning. I also changed "100 requests a minute" to 250 in the docstring in `geo/client.py` and in `docs/geocoding.md`.

`Throttle` and the existing test read the constant, so they needed no changes.
