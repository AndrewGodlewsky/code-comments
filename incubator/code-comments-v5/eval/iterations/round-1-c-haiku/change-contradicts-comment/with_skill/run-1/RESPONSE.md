I raised the geocoding request limit from 100 to 250 requests a minute.

Changes:
- `geo/limits.py`: `REQUESTS_PER_MINUTE = 250`. The comment keeps the Geoway free-tier fact (100 requests a minute, HTTP 429 when exceeded). The old "keep this at or below the quota" advice no longer holds, so it now says this limit is above that quota and relies on the API key having a higher one.
- `geo/client.py`: the module docstring now says the client sends at most 250 requests a minute.
- `docs/geocoding.md`: now says the client sends at most 250 requests a minute, spaced evenly.

Please check two things:
1. The free-tier quota is 100 requests a minute, so 250 only works if the API key has a higher quota. I could not confirm that from the repository. Please confirm the key's quota is at least 250 a minute before this ships. Going over it returns HTTP 429.
2. The code does not record why the limit moved, and I did not invent a reason. If there is a ticket or plan for the higher quota, add its reference beside the constant in `geo/limits.py`.

Tests: `python -m unittest tests.test_client` passes (2 tests). Both tests read the constant or pass their own rate, so they did not need changes.
