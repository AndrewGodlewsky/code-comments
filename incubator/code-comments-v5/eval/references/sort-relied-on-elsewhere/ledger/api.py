"""Account balances for the finance dashboard."""
from collections import defaultdict

from ledger.rows import fetch_rows


def balances(conn):
    """Return {"accounts": {account: pence}, "total": pence} over every ledger row."""
    per_account = defaultdict(int)
    for row in fetch_rows(conn):
        per_account[row.account] += row.amount_pence
    return {"accounts": dict(per_account), "total": sum(per_account.values())}
