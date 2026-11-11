I raised `PAGE_SIZE` in `exporter/config.py` from 50 to 200. That is under the ledger API's 500-row cap in `docs/limits.md`. I did not run the tests.

I also corrected three places that still said 50 and described the current code:
- `exporter/client.py`: the module docstring now says 200 rows per request.
- `exporter/sync.py`: the module docstring now says "200 at a time" instead of "fifty at a time".
- `docs/api.md`: now says results come back 200 rows per page.

I left these alone because they record history or outside facts:
- `CHANGELOG.md`: the entry about moving from 20 to 50 rows is history. I did not add a new entry for this change, so add one if you keep them for every change.
- `docs/reports/2026-03-14-load-test.md`: this dated report measured 50-row pages (1,940 requests, 11 minutes).
- `docs/limits.md`: the 500-row cap is the ledger team's limit, not ours.

The tests use `PAGE_SIZE` rather than a hard-coded number, so they need no change.

The load-test numbers were measured at 50 rows, so they do not predict the new run time. Moving to 200-row pages should cut the request count to roughly a quarter. Check that the 30-second request timeout still holds with larger pages, and the 120-requests-a-minute key limit will be easier to stay under.
