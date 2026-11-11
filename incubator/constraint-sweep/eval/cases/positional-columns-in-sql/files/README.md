# ledger-export

Exports cleared ledger entries as a nightly CSV file.

- `exporter/rows.py`: the `Entry` record and `cleared_entries`.
- `exporter/csv_out.py`: writes the CSV (`write_csv`).
- `exporter/cli.py`: `python -m exporter.cli OUT.csv < records.json` writes tonight's file.
- `reports/monthly.py`: the monthly totals finance asks for, read from the nightly files.
- `docs/finance.md`: notes for the finance team.
- `deploy/`: production cron entries and the jobs they run.
