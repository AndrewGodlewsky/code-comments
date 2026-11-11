The export page size is now 200 rows, up from 50.

- `exporter/config.py`: `PAGE_SIZE = 200`.
- `docs/api.md`: updated "50 rows per page" to 200 so the docs match.

200 is under the ledger API's 500-row cap in `docs/limits.md`, so requests won't be rejected. A run should also make about a quarter as many requests, which keeps it well inside the 120 requests/minute key limit. The existing tests pass, and they use `PAGE_SIZE` rather than a hard-coded 50.

One thing I couldn't check: `REQUEST_TIMEOUT_S` is still 30 seconds per page, and each page is now 4x larger. If the ledger API is slow on big pages, a request could time out and fail the night's run. Watch the first month-end run, and raise the timeout if that happens.
