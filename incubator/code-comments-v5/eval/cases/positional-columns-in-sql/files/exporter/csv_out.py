"""Write ledger entries as the nightly CSV export."""
import csv

COLUMNS = ["id", "account", "amount", "ts"]


def write_csv(entries, fh):
    """Write a header row, then one row per entry."""
    writer = csv.writer(fh, lineterminator="\n")
    writer.writerow(COLUMNS)
    for entry in entries:
        writer.writerow([getattr(entry, column) for column in COLUMNS])
