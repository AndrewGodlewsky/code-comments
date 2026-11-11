The export page size is now 200 rows.

What changed:
- `exporter/config.py`: `PAGE_SIZE` is 200 (was 50). This is the only code change, so every request now asks for 200 rows.
- `exporter/client.py`: the module docstring now says `fetch_changed()` asks for 200 rows per request.
- `exporter/sync.py`: the module docstring now says "two hundred at a time" (was "fifty").
- `docs/api.md`: results now come back 200 rows per page (was 50).

Checks: `python -m unittest` passes (3 tests). A sweep for the old value (50, fifty, "50 rows", 20 and the 1,940 request count) found no other living descriptions that state the old value.

Kept as written:
- `CHANGELOG.md`, 0.3.0 entry ("Requests now ask for 50 rows a page instead of 20."): a released record. There is no `Unreleased` heading, so I did not add a changelog line. Add one if you want this change logged.
- `docs/reports/2026-03-14-load-test.md`: a dated record of the March run at 50-row pages. Its figure of 1,940 requests describes that run. The same row count at 200 rows would be roughly 485 requests (1,940 × 50 / 200), which is arithmetic only and not measured.

Outside facts:
- `docs/limits.md` says the ledger API rejects requests for more than 500 rows. 200 is under that limit, so nothing breaks.
- The 120 requests a minute limit still holds. Fewer, larger requests make it less likely to be reached.

Drift not caused by this change: none found.
