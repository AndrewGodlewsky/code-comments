The export page size is now 200 rows, up from 50. Month-end exports should make about a quarter as many requests.

The ledger API rejects requests above 500 rows, so 200 is inside its limit. The 2026-03-14 load test also reported that the ledger team was fine with pages up to 500.

Changes:
- `exporter/config.py`: `PAGE_SIZE = 200`. The client, sync and tests all read this constant, so nothing else needed a number change.
- `exporter/client.py` and `exporter/sync.py`: docstrings no longer say 50 or "fifty".
- `docs/api.md`: now says 200 rows per page.
- `CHANGELOG.md`: added an Unreleased entry.

The unit tests pass (3 tests, `python -m unittest`). I did not run the export against the ledger's staging API, so the real request count and run time at 200 rows are still unmeasured.
