"""Write ledger rows as CSV."""
import csv

HEADER = ["id", "account", "amount", "memo"]


def write_rows(rows, fh):
    """Write a header line, then one line per row, in the order given."""
    writer = csv.writer(fh, lineterminator="\n")
    writer.writerow(HEADER)
    for row in rows:
        writer.writerow([row.id, row.account, f"{row.amount_pence / 100:.2f}", row.memo])
