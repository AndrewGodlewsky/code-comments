I raised the export page size from 50 to 200 rows (`PAGE_SIZE` in `exporter/config.py`). I did not run the tests.

200 is under the ledger API's 500-row cap in `docs/limits.md`. A night's export now makes about a quarter as many requests, which also keeps it further from the 120 requests a minute key limit.

I corrected these places that still said 50 or "fifty":
- `exporter/client.py` module docstring: now "200 rows per request".
- `exporter/sync.py` module docstring: "fifty at a time" is now "200 at a time".
- `docs/api.md`: "Results come back 200 rows per page".

I left these as they were:
- `CHANGELOG.md` ("50 rows a page instead of 20") is a historical entry. I did not add a new entry for this change.
- `docs/reports/2026-03-14-load-test.md` is a dated report. Its 50-row figures (1,940 requests, 11 minutes) describe that test run, and the 200-row page size has not been load-tested.
- `docs/limits.md` (500-row cap, 120 requests a minute) states the ledger team's limits, not ours.

I found no mismatches that my change did not cause. The tests use `PAGE_SIZE` rather than a hard-coded 50, so they needed no edits.

One thing to check: the 30-second per-request timeout (`REQUEST_TIMEOUT_S`) was chosen when pages were 50 rows. Larger pages may take longer to return, so it's worth confirming 200-row latency stays well under it.
