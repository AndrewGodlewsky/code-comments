The export page size is now 200 rows. The change is `PAGE_SIZE = 200` in `exporter/config.py`. The unit tests pass (`python -m unittest`, 3 tests).

I also corrected the prose that still stated 50 rows:
- `exporter/client.py`: the `fetch_changed()` docstring now says 200 rows per request.
- `exporter/sync.py`: the module docstring now says "two hundred at a time".
- `docs/api.md`: results now say they come back 200 rows per page.

Kept as written:
- `CHANGELOG.md` 0.3.0 entry ("Requests now ask for 50 rows a page instead of 20"). It is a released entry, so it is a record. I did not add a changelog line because there is no `Unreleased` heading. You may want to add one for this change.
- `docs/reports/2026-03-14-load-test.md` (50-row pages, 1,940 requests, 11 minutes). It is a dated report, so it is a record and describes the March run.
- `docs/limits.md` says the ledger API rejects requests for more than 500 rows. This is an outside fact set by the ledger team. 200 is under that limit, so the change does not break it.

Drift not caused by this change: none found.
