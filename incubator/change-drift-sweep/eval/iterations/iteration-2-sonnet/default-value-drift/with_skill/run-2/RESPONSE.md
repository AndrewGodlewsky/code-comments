Raised the export page size from 50 to 200 rows.

Changed:
- `exporter/config.py`: `PAGE_SIZE = 200`.
- `exporter/client.py` docstring: "asks for 200 rows per request".
- `exporter/sync.py` docstring: "fifty at a time" -> "200 at a time".
- `docs/api.md`: "Results come back 200 rows per page".

Searched digits, "fifty", the old 20 and the derived 1,940 request count. Tests use `PAGE_SIZE`, so they need no edit (not run).

Kept as written:
- `CHANGELOG.md` 0.3.0 entry ("50 rows a page instead of 20"): released record. There is no `Unreleased` heading, so I added no line; add one if you want this noted.
- `docs/reports/2026-03-14-load-test.md` (50-row pages, 1,940 requests, 11 minutes): dated report. At 200 rows the same night would need roughly 485 requests (1,940 / 4), but that is a projection, not a measurement.

Outside facts, still satisfied:
- `docs/limits.md`: the API rejects requests over 500 rows, so 200 is within it. The ledger team's "up to 500 rows is fine" also covers 200.
- The 120 requests/minute key limit is not at risk, since fewer requests are made.

No drift that predated this change was found.
