Raised the export page size from 50 to 200 rows. The value lives in `PAGE_SIZE` in `exporter/config.py`, and the client and tests read it from there. 200 is within the ledger API's 500-row limit (`docs/limits.md`).

I also updated the places that stated the old number so they don't contradict the code: the docstring in `exporter/client.py`, the "fifty at a time" wording in `exporter/sync.py`, `docs/api.md`, and a new "Unreleased" entry in `CHANGELOG.md`. I left the 0.3.0 changelog entry and the 2026-03-14 load-test report alone, since they record what was true then.

The unit tests pass. I did not run a real export, so I haven't measured the speedup. The 30-second per-request timeout (`REQUEST_TIMEOUT_S`) was set with 50-row pages in mind; 200-row pages take longer per request, so watch the first month-end run for timeouts.
