"""Render an invoice as plain text."""

from billing.totals import compute_total


def render(lines):
    rows = [f"{q} x {p}" for q, p in lines]
    # compute_total() rounds each line before summing, so the printed total can
    # differ from the unrounded sum by a few pence.
    rows.append(f"Total: {compute_total(lines)}")
    return "\n".join(rows)
