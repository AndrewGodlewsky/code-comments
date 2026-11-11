The export page size is now 200 rows, up from 50. The change is in `exporter/config.py` (`PAGE_SIZE = 200`). The unit tests pass (`python -m unittest`, 3 tests).

I also updated the text that described the old size: the docstrings in `exporter/client.py` and `exporter/sync.py`, and `docs/api.md`. I added an Unreleased entry to `CHANGELOG.md`.

Points to check before this ships:

- The 200-row size has not been load-tested. The only load test in `docs/reports/2026-03-14-load-test.md` ran with 50-row pages (11 minutes, 1,940 requests). The ledger team said pages of up to 500 rows are fine, so 200 is within their limit. Please time a month-end-sized run in staging to confirm the speed-up you expect.
- The ledger API rejects requests above 500 rows (`docs/limits.md`). 200 is well under that, so nothing conflicts with the limit.
