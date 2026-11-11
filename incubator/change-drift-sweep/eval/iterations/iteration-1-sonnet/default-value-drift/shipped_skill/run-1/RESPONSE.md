The export page size is now 200 rows (`PAGE_SIZE` in `exporter/config.py`, was 50). I did not run the tests.

Updated the statements that described the old size so none still say 50:
- the `fetch_changed()` module docstring in `exporter/client.py`
- the `exporter/sync.py` module docstring ("fifty at a time" is now "200 at a time")
- `docs/api.md` ("50 rows per page" is now 200)
- a new "Unreleased" entry in `CHANGELOG.md`

Left alone on purpose:
- `docs/limits.md`: the ledger API's 500-row cap per request. 200 is within it, and that limit is the ledger team's.
- `docs/reports/2026-03-14-load-test.md`: a dated record of the 50-row run.

Open points:
- I wrote no reason into the code. The 200 comes from your request and the ledger team's OK, and I found no recorded rationale. Tell me if you want one added.
- Pages are 4x larger and the per-request timeout is still 30 seconds (`REQUEST_TIMEOUT_S`). The 14 March load test only measured 50-row pages (p95 120 ms), so I can't confirm 200-row pages stay well under the timeout. Worth checking on staging before month-end.
- I made up the "Unreleased" heading and did not pick a version number. Rename it to whatever your release process uses.
