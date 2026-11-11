Raised the export page size to 200 rows (`PAGE_SIZE` in `exporter/config.py`, was 50). 200 is under the ledger API's 500-row cap. Tests pass.

Corrected, by file (old figure only):
- `exporter/config.py`: `PAGE_SIZE = 200`.
- `exporter/client.py`: module docstring now says 200 rows per request.
- `exporter/sync.py`: module docstring now says "two hundred at a time" (word kept as a word).
- `docs/api.md`: "200 rows per page".

Kept as written:
- `CHANGELOG.md` 0.3.0 entry ("50 rows a page instead of 20"): released record. There is no `Unreleased` heading, so I added no changelog line; add one if you want this change noted.
- `docs/reports/2026-03-14-load-test.md`: dated report. Its 50-row, 1,940-request, 11-minute figures describe that test, not the current setting. At 200 rows the same export would take about 485 requests (1,940 x 50 / 200), but that is an estimate, not a measured result.
- `docs/limits.md`: the ledger team's 500-row cap and 120 requests/minute are outside facts. 200 rows is within the cap, and fewer requests per night stays within the rate limit.

No instruction files were touched. No pre-existing drift found. The 30-second timeout is unchanged; the timeout per page was only load-tested with 50-row pages, so larger pages may take longer per request. Worth a check on staging.
