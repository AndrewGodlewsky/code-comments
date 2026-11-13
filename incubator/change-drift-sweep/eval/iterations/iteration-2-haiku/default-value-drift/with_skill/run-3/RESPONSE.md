The export page size is now 200 rows. The change is `PAGE_SIZE = 200` in `exporter/config.py`. The tests pass (`python -m unittest`, 3 tests).

I also corrected the prose that still said 50:
- `exporter/client.py`: the `fetch_changed()` docstring now says it asks for `PAGE_SIZE` rows per request, not 50.
- `exporter/sync.py`: the module docstring now says rows are pulled "a page at a time" instead of "fifty at a time".
- `docs/api.md`: results now say "200 rows per page", not 50.

Left unchanged on purpose:
- `CHANGELOG.md` 0.3.0 entry ("ask for 50 rows a page instead of 20"): a released entry, so it stays as written. I did not add a changelog line because there is no `Unreleased` heading.
- `docs/reports/2026-03-14-load-test.md`: a dated report about 50-row pages. It stays as written.
- `docs/limits.md`: the ledger API rejects requests for more than 500 rows. This is an outside fact set by the ledger team. 200 is within it.

No derived figures in living docs depended on 50. The 30-second timeout is unchanged.

Ledger team note: 200 is under the 500-row limit. The 120 requests per minute per key limit is unaffected by the page size. Requests per night drop roughly fourfold (the 14 March load test made 1,940 requests with 50-row pages).
