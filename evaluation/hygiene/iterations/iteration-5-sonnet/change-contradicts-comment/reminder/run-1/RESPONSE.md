I raised `REQUESTS_PER_MINUTE` in `geo/limits.py` from 100 to 250. The throttle and its test both read that constant, so the spacing between calls follows automatically.

I also updated the places that said 100:
- the module docstring in `geo/client.py`
- `docs/geocoding.md`
- the comment in `geo/limits.py`, which called 100 the free-tier quota. It now says the free tier is 100 a minute and that 250 needs a plan that allows it.

I haven't run the tests.

Please confirm our Geoway key is on a plan that allows 250 a minute. If it is still on the free tier, Geoway will return HTTP 429 for the rest of each minute once we pass 100.
