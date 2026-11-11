The export page size is now 200 rows, up from 50. The change is in `exporter/config.py` (`PAGE_SIZE = 200`), and the code that reads it needed no changes.

I also updated the places that described the old size: the `docs/api.md` page-size line, the `exporter/client.py` and `exporter/sync.py` docstrings, and a new "Unreleased" entry in `CHANGELOG.md`.

The ledger API accepts up to 500 rows per request (`docs/limits.md`), so 200 is within its limit. The 120 requests-a-minute key limit is also not a concern: at 200 rows a page, the 2026-03 month-end replay would need roughly 485 requests instead of 1,940. The unit tests pass (`python -m unittest`, 3 tests).

I have not run a real month-end night against the ledger API. The first run at the new size is worth watching, especially the request latency and the 30-second timeout.
