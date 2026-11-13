The export page size is now 200 rows, up from 50. The ledger API accepts up to 500 rows per request (docs/limits.md), so 200 is within its limit, and the ledger team has said pages up to 500 are fine.

Changes:
- exporter/config.py: `PAGE_SIZE = 200`. The client and the tests both read this constant, so no other code needed the number.
- exporter/client.py and exporter/sync.py: docstrings no longer hard-code "50" (client now refers to PAGE_SIZE).
- docs/api.md: states 200 rows per page and points at the 500-row limit.
- CHANGELOG.md: added an Unreleased entry.

The unit tests pass (`python -m unittest`, 3 tests). I did not run against the real ledger API, so the night's runtime improvement is not measured yet. Expect fewer requests (roughly 1,940 at 50 rows per page in the March load test, about a quarter of that at 200), though the request rate limit of 120 per minute per key still applies. The March report at 50-row pages took 11 minutes, so a rerun against staging would confirm the gain.

I left docs/reports/2026-03-14-load-test.md unchanged because it records the earlier run.
