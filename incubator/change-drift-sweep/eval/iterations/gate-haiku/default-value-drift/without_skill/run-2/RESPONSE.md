The export page size is now 200 rows, up from 50.

What changed:
- `exporter/config.py`: `PAGE_SIZE = 200`. The client and the tests both read this constant, so the request size follows it.
- Comments and docs that still said 50 now match: `exporter/client.py`, `exporter/sync.py`, `docs/api.md`.
- `CHANGELOG.md`: an "Unreleased" entry records the change.

Checks:
- The ledger API rejects requests over 500 rows (`docs/limits.md`), so 200 is within its limit.
- The unit tests pass (`python -m unittest`, 3 tests).

Not verified:
- The 14 March load test (`docs/reports/2026-03-14-load-test.md`) was run with 50-row pages only. I have not timed a 200-row run against the ledger staging copy, so the speed-up for month-end nights is expected, not measured. Running the month-end replay at 200 rows before the next close would confirm it.
- The ledger allows 120 requests a minute per key. At 200 rows a page, a month-end run should need roughly 490 requests instead of 1,940, so the rate limit should not be a problem.
