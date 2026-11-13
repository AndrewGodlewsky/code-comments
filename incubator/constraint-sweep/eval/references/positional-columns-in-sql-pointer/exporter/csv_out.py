"""Write ledger entries as the nightly CSV export."""
import csv

# deploy/warehouse/load_ledger.sql reads these fields by position.
COLUMNS = ["id", "account", "amount", "currency", "ts"]


def write_csv(entries, fh):
    """Write a header row, then one row per entry."""
    writer = csv.writer(fh, lineterminator="\n")
    writer.writerow(COLUMNS)
    for entry in entries:
        writer.writerow([getattr(entry, column) for column in COLUMNS])
