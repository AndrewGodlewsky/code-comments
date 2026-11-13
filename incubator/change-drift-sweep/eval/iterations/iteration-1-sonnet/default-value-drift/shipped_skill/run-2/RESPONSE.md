Raised `PAGE_SIZE` in `exporter/config.py` from 50 to 200. 200 is within the ledger API's 500-row cap (`docs/limits.md`), and the ledger team's OK for pages up to 500 is recorded in the March load test. Tests pass.

Comment and doc fixes so nothing still says 50:
- `exporter/client.py` module docstring now says "PAGE_SIZE rows" instead of "50 rows", so it can't go stale again.
- `exporter/sync.py` module docstring said "fifty at a time"; it now says "in pages of PAGE_SIZE rows".
- `docs/api.md` now says 200 rows per page.
- I added a note beside `PAGE_SIZE` that the API rejects requests over 500 rows, pointing to `docs/limits.md`.

Left alone:
- `CHANGELOG.md`. Add a line when you pick the release version.
- `docs/reports/2026-03-14-load-test.md`. It is a dated record of the 50-row run, so it stays as written.

Please check one thing. The load test only covered 50-row pages, so I haven't seen latency or timeout figures for 200. The 30-second timeout is probably fine, but month-end is worth watching on the first run.
