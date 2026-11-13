"""Cleared ledger entries, as the exporter sees them."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    id: str
    account: str
    amount: str  # a decimal string such as "12.50", never a float
    currency: str  # ISO 4217 code, such as "EUR"
    ts: str  # ISO 8601, UTC
    memo: str = ""


def cleared_entries(records):
    """Build an Entry for each raw record that has cleared, in the order given."""
    return [Entry(r["id"], r["account"], r["amount"], r["currency"], r["ts"], r.get("memo", ""))
            for r in records if r.get("cleared")]
