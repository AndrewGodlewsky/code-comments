I raised the export page size from 50 to 200 rows in `exporter/config.py` (`PAGE_SIZE`). The ledger API rejects requests above 500 rows (`docs/limits.md`), so 200 is within the limit. The unit tests pass (`python -m unittest`, 3 tests).

Comments and docs that described the old size are corrected:
- `exporter/client.py`: the module docstring now says `PAGE_SIZE` rows instead of "50 rows".
- `exporter/sync.py`: the docstring now says "a page at a time" instead of "fifty at a time".
- `docs/api.md`: the page size now points to `PAGE_SIZE` in `exporter/config.py` instead of stating 50.
- `exporter/config.py`: the `PAGE_SIZE` comment now records that the ledger API caps requests at 500 rows, so the value must stay at or below that.

Things to check:
- No reason for choosing 200 specifically (rather than, say, 500, the cap) was given, so the code records only the value and the cap. If you can tell me why 200 was chosen, I will add that reason beside `PAGE_SIZE`.
- `CHANGELOG.md` is unchanged. Its 0.3.0 entry ("Requests now ask for 50 rows a page") is accurate history, so I left it alone. Add a new entry if you want this change recorded.
- `docs/reports/2026-03-14-load-test.md` measures the 50-row run (1,940 requests, 11 minutes). It is a dated report, so I did not change it. The new run will need its own measurement.
