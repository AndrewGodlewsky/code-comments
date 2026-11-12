"""Read ledger rows."""
from collections import namedtuple

Row = namedtuple("Row", "id account amount_pence memo")


def fetch_rows(conn):
    """Return the ledger rows."""
    cursor = conn.execute("SELECT id, account, amount_pence, memo FROM entries")
    rows = [Row(*record) for record in cursor.fetchall()]
    rows.sort(key=lambda row: row.id)
    return rows
