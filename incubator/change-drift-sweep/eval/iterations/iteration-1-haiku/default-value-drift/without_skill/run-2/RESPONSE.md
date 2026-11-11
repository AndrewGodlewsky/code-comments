I've raised the export page size from 50 to 200 rows.

What changed:
- `exporter/config.py`: `PAGE_SIZE` is now 200. The client and tests read this constant, so nothing else needed the number.
- `exporter/client.py` and `exporter/sync.py`: docstrings no longer say "50 rows" or "fifty at a time".
- `docs/api.md`: now says the exporter asks for 200 rows per page and notes the ledger's 500-row limit.
- `CHANGELOG.md`: added an Unreleased entry.

Checks:
- The ledger API rejects requests for more than 500 rows (`docs/limits.md`), so 200 is within the limit.
- The March 2026 load test (`docs/reports/2026-03-14-load-test.md`) found pages of up to 500 rows acceptable to the ledger team. Per-request latency was well under the 30-second timeout.
- The unit tests pass (`python -m unittest`, 3 tests).

Not verified here: I could not run the exporter against the real ledger API or staging, so the speedup is expected rather than measured. The 2026-03 load test showed 1,940 requests and 11 minutes at 50 rows; at 200 rows the same night should need about a quarter of the requests. Please confirm with a staging run before the next month-end.
