The export page size is now 200 rows, up from 50. The change is in `exporter/config.py` (`PAGE_SIZE = 200`), and `python -m unittest` passes (3 tests).

Current descriptions of the old value that I corrected:
- `exporter/client.py` module docstring: "asks for 50 rows per request" now says 200.
- `exporter/sync.py` module docstring: "fifty at a time" now says "two hundred at a time".
- `docs/api.md`: "Results come back 50 rows per page" now says 200.

Left unchanged on purpose:
- `CHANGELOG.md` 0.3.0 entry ("Requests now ask for 50 rows a page instead of 20."). It is a historical entry. I did not add a new changelog entry for this change; you may want one.
- `docs/reports/2026-03-14-load-test.md`. It is a dated report whose figures (1,940 requests, 11 minutes) were measured with 50-row pages. They no longer describe the current code, but the report is a dated record, so I left it as written.

Checked and consistent:
- `docs/limits.md` says the ledger API rejects requests above 500 rows. 200 is under that limit.
- The 30-second request timeout is unaffected.
- The tests use `PAGE_SIZE` and needed no edits.

Mismatches not caused by this change: none in the current docs. The only stale figures are the two historical records above.
