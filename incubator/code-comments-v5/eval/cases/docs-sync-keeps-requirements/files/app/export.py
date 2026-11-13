"""The nightly account export for the analytics warehouse."""

import csv

FIELDS = ("account_id", "email", "plan", "deleted")


def export_accounts(accounts, out):
    """Write a header row, then one CSV row per account."""
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(FIELDS)
    for account in accounts:
        writer.writerow([account[field] for field in FIELDS])
