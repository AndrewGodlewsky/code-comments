I raised the export page size to 200 rows by changing `PAGE_SIZE` from 50 to 200 in `exporter/config.py`. The tests pass. 200 is under the ledger API's 500-row limit.

I also swept the prose for the old value (50, "fifty", and the figures derived from it) and corrected the three places that still said 50:
- `exporter/client.py`: the module docstring now says 200 rows per request.
- `exporter/sync.py`: the module docstring now says "200 at a time" (it was "fifty at a time").
- `docs/api.md`: now says results come back 200 rows per page.

I left these unchanged:
- `CHANGELOG.md`: the 0.3.0 entry ("50 rows a page instead of 20") is a released record. There is no `Unreleased` heading, so I added no line. Add one if you want this change noted.
- `docs/reports/2026-03-14-load-test.md`: a dated report. Its "50-row pages" and "1,940 requests" figures were true when measured. Its "pages of up to 500 rows are fine" is the ledger team's statement, kept as written.
- `docs/limits.md`: the 500-row cap and the 120 requests per minute per key are the ledger team's limits. 200 rows is within the cap. Fewer requests per night means the rate limit matters less.

No drift existed before this change.

Not changed: `REQUEST_TIMEOUT_S` stays at 30 seconds. The timeout was tested only against 50-row pages, so check that larger pages stay well under it.
