"""Render an invoice as plain text."""

from billing.totals import invoice_total


def render(lines):
    rows = [f"{q} x {p}" for q, p in lines]
    # invoice_total() rounds each line before summing, so the printed total can
    # differ from the unrounded sum by a few pence.
    rows.append(f"Total: {invoice_total(lines)}")
    return "\n".join(rows)
