I raised `PAGE_SIZE` in `exporter/config.py` from 50 to 200, so each request to the
ledger API now asks for 200 rows.

Updated the descriptions that gave the old size: the `exporter/client.py` docstring,
the `exporter/sync.py` docstring ("fifty at a time") and `docs/api.md`.

Left as written:
- `docs/reports/2026-03-14-load-test.md` and the 0.3.0 CHANGELOG entry. They record
  what was true at the time.
- `docs/limits.md`: the ledger team's 500-row limit. 200 is within it.

The tests pass.
