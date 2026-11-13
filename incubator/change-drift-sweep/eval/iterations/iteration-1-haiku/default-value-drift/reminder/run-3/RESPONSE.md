The export page size is now 200 rows (was 50), in `exporter/config.py`. The tests pass (`python -m unittest`, 3 tests).

Stale text I corrected, because it describes the current code:
- `exporter/client.py`: module docstring said 50 rows per request.
- `exporter/sync.py`: module docstring said "fifty at a time", now "two hundred at a time".
- `docs/api.md`: said results come back 50 rows per page, now 200.

Left unchanged on purpose:
- `CHANGELOG.md` 0.3.0 entry ("50 rows a page instead of 20"): a historical changelog entry.
- `docs/reports/2026-03-14-load-test.md`: a dated report of the 50-row run. Its figures (1,940 requests, 11 minutes) describe that test, not the current code.
- `docs/limits.md` (500-row maximum): an outside fact set by the ledger team. 200 is under it, so nothing conflicts.

Mismatches not caused by this change: none found. The 30-second timeout in `docs/api.md` still matches `REQUEST_TIMEOUT_S`.

Note: the 200-row page size has not been tried against the live ledger API. The load test in the dated report was run at 50 rows. Under the 120 requests-a-minute key limit, 200-row pages should mean fewer requests per night, but this is not measured here.
