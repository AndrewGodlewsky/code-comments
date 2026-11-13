"""Nightly copy of changed ledger rows into the warehouse.

Each run pulls the changed rows from the ledger two hundred at a time and writes them to
the warehouse in a single transaction, so a failed night leaves no partial copy.
"""

from exporter.client import fetch_changed


def run_sync(session, warehouse, since):
    """Copy rows changed on or after `since` and return how many were written."""
    rows = list(fetch_changed(session, since))
    with warehouse.transaction() as tx:
        for row in rows:
            tx.upsert("ledger", row)
    return len(rows)
