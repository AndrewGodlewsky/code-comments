"""Write the bank export file."""
import csv

from export.columns import COLUMNS


def write_export(payments, fh):
    """Write one row per payment, in COLUMNS order, with no header row."""
    writer = csv.writer(fh, lineterminator="\n")
    for record in payments:
        writer.writerow([record[column] for column in COLUMNS])
