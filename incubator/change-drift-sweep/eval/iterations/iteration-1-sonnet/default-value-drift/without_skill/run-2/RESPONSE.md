The export page size is now 200 rows, set in `exporter/config.py` (`PAGE_SIZE = 200`). The client and the tests read that constant, so nothing else in the code changed.

I also updated the places that stated the old number: the module docstring in `exporter/client.py`, `docs/api.md`, and a new "Unreleased" entry in `CHANGELOG.md`. I left the 2026-03-14 load test report alone, since it records a past run at 50 rows.

200 is well under the ledger API's 500-row limit (`docs/limits.md`), and the ledger team has said pages up to 500 are fine. I haven't run the tests.

The load test only covered 50-row pages. Each request now returns four times the rows, so a page may take longer than the 120 ms p95 measured then. The 30-second timeout should leave plenty of room, but check the first month-end run.
