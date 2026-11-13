The export page size is now 200 rows (`PAGE_SIZE` in `exporter/config.py`). 200 is under the ledger team's 500-row cap. The tests pass.

I swept the prose for the old value. That covered "50", "fifty" and derived figures. The requests/minute limit and the timeout don't depend on page size.

**Corrected**
- `exporter/client.py`: module docstring said 50 rows per request, now 200.
- `exporter/sync.py`: module docstring said "fifty at a time", now "two hundred at a time" (kept as a word).
- `docs/api.md`: "50 rows per page" is now "200 rows per page".

**Kept word for word**
- `CHANGELOG.md` 0.3.0 entry ("50 rows a page instead of 20"): a released record. There is no `Unreleased` heading, so I added no changelog line.
- `docs/reports/2026-03-14-load-test.md`: a dated report. Its "50-row pages, 1,940 requests, 11 minutes" figures are true of that test. At 200 rows the same night would need about 485 requests (1940 x 50 / 200), but that is an estimate, not a measurement.
- `docs/limits.md`: the 500-row cap and the 120 requests/minute limit are the ledger team's. The change is within both, so they are unaffected.

**Drift not caused by this change**
- None found.
