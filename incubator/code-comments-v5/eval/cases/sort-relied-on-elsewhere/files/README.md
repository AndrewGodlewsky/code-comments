# ledger-export

Reads the general ledger and exports it every night.

- `ledger/db.py` opens the ledger database and loads entries.
- `ledger/rows.py` reads ledger rows (`fetch_rows`).
- `ledger/csv_out.py` writes rows as CSV.
- `ledger/nightly.py` writes the nightly export file: `python -m ledger.nightly DB OUT.csv`.
- `ledger/api.py` serves account balances to the finance dashboard.
- `ops/` holds the cron table and the scripts it runs.

Release notes are in CHANGELOG.md. Run the tests with `python -m unittest`.
