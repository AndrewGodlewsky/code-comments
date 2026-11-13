The export page size is now 200 rows. `PAGE_SIZE` in `exporter/config.py` changed from 50 to 200, and the tests pass (`python -m unittest`, 3 tests OK).

Living descriptions I corrected, so they stop saying 50:
- `exporter/client.py`: the `fetch_changed()` docstring now says it asks for 200 rows per request.
- `exporter/sync.py`: the module docstring now says "two hundred at a time" (kept as a word, matching its spelled-out form).
- `docs/api.md`: now says results come back 200 rows per page.

Kept as written:
- `CHANGELOG.md` 0.3.0 entry ("50 rows a page instead of 20"): a released record.
- `docs/reports/2026-03-14-load-test.md`: a dated report on the 50-row run (1,940 requests, 11 minutes). It stays true for its date.
- `docs/limits.md`: the ledger API rejects requests over 500 rows. 200 is under that, so nothing breaks. No change needed.
- `REQUEST_TIMEOUT_S` (30 s) and the 120-requests-a-minute key limit are unaffected by the page size.

Not added: there is no `Unreleased` heading in `CHANGELOG.md`, so I did not add a changelog line. Someone should decide whether to add one for 200-row pages.

Drift not caused by this change: none found.

Worth knowing: pages are 4 times larger, so each night makes about a quarter of the requests. The load test measured 50-row pages only. The 200-row setting has not been timed against the ledger staging copy, and the ledger team's stated tolerance (up to 500 rows) is the only evidence it is safe.
