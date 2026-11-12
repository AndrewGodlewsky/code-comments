"""Read ledger rows."""
from collections import namedtuple

Row = namedtuple("Row", "id account amount_pence memo")


def fetch_rows(conn):
    """Return the ledger rows in id order."""
    # ops/nightly.sh uploads the export in this order, and the bank rejects the file
    # unless ids ascend. id is the primary key, so the database returns this order.
    cursor = conn.execute("SELECT id, account, amount_pence, memo FROM entries ORDER BY id")
    return [Row(*record) for record in cursor.fetchall()]
