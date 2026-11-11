The export page size is now 200 rows, up from 50. `PAGE_SIZE` in `exporter/config.py` is 200, and the unit tests pass (`python -m unittest`, 3 tests).

I also corrected the prose that still said 50:
- `exporter/client.py`: the module docstring now says `fetch_changed()` asks for 200 rows per request.
- `exporter/sync.py`: the module docstring now says the rows are pulled "two hundred at a time".
- `docs/api.md`: results now "come back 200 rows per page".

Kept as written:
- `CHANGELOG.md` 0.3.0 entry ("Requests now ask for 50 rows a page instead of 20"): a released record.
- `docs/reports/2026-03-14-load-test.md`: a dated load test. It measured 50-row pages (1,940 requests, 11 minutes), so it stays as it was.
- `docs/limits.md` (the ledger API rejects requests above 500 rows): an outside fact set by the ledger team. 200 is within it.

I did not add a changelog line, because the changelog has no `Unreleased` heading.

Note: the load test ran at 50 rows with p95 page latency of 120 ms, well under the 30-second timeout. It did not test 200-row pages, so the bigger pages are unmeasured. Run a staging replay before relying on the faster night.
