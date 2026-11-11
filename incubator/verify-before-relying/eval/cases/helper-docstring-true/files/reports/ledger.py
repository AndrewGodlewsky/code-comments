"""The monthly ledger that finance reconciles against the bank statement."""

from money.rounding import round_cents


def ledger_rows(entries):
    """Return a (date, description, amount) row per entry, with amounts rounded to the cent."""
    return [(entry["date"], entry["description"], round_cents(entry["amount"])) for entry in entries]
