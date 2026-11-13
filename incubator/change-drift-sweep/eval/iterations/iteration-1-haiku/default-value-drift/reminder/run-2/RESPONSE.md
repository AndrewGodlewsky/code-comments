The export page size is now 200 rows.

Changed `PAGE_SIZE` from 50 to 200 in `exporter/config.py`. Updated the docs that describe the current code to match:

- `exporter/client.py` docstring: "asks for 200 rows per request".
- `exporter/sync.py` docstring: "two hundred at a time" (was "fifty at a time").
- `docs/api.md`: "Results come back 200 rows per page".

Left unchanged on purpose:

- `CHANGELOG.md` 0.3.0 entry ("50 rows a page instead of 20"). It is a historical record.
- `docs/reports/2026-03-14-load-test.md`. It is a dated report, so its "50-row pages" and "1,940 requests" figures stay as measured. The request count at 200 rows will be lower.
- `docs/limits.md`. The ledger API's 500-row cap is an outside fact, and 200 is under it.

Mismatches I did not cause: none found. The unit tests pass (`python -m unittest`, 3 tests). They read `PAGE_SIZE`, so they needed no edits.

Nothing was committed, and no git, GitHub or task tracking was used.
