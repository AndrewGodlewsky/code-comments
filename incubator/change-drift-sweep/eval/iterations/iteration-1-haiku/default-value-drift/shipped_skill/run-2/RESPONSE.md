The export page size is now 200 rows. Change made in `exporter/config.py` (`PAGE_SIZE = 200`).

Comments and docs that described the old 50-row page were corrected to match:
- `exporter/config.py`: the `PAGE_SIZE` comment now notes the reason for the larger page and that the ledger API rejects requests above 500 rows (`docs/limits.md`). 200 is within that limit.
- `exporter/client.py`: the module docstring refers to `PAGE_SIZE` instead of a hard-coded 50.
- `exporter/sync.py`: the module docstring says "a page at a time" instead of "fifty at a time".
- `docs/api.md`: now says results come back 200 rows per page.

The unit tests pass (`python -m unittest`, 3 tests).

Left unchanged on purpose:
- `docs/reports/2026-03-14-load-test.md` and the 0.3.0 entry in `CHANGELOG.md` record the earlier 50-row runs and are dated history.
- `CHANGELOG.md` has no entry for this change. Add one if you keep a changelog for each release.

Two things to check before the next month-end run:
- The 14 March load test measured 50-row pages only. 200-row pages have not been measured here, so the faster run time is expected but not verified.
- The ledger team's agreement to bigger pages is taken from your message. I did not find a written record of it in the repository.
