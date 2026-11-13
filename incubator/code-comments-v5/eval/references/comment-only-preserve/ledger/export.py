# Copyright 2025 Northwind Ledger Ltd.
# SPDX-License-Identifier: Apache-2.0
"""Export ledger entries as CSV for the accounts team."""

import csv
import io

# Spreadsheet apps run a cell that starts with =, +, - or @ as a formula, so
# memos that start with one are prefixed with a quote.
FORMULA_PREFIXES = ("=", "+", "-", "@")

HEADER = ["date", "account", "amount", "memo"]


def export_csv(entries):  # noqa: C901
    """Return the entries as CSV text, oldest entry first."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(HEADER)
    for entry in sorted(entries, key=lambda e: e["date"]):
        # Amounts are stored in pence; the accounts team wants pounds.
        pounds = entry["amount_pence"] / 100
        writer.writerow([entry["date"], entry["account"], f"{pounds:.2f}", _safe(entry["memo"])])
    return out.getvalue()


def _safe(memo):
    if memo.startswith(FORMULA_PREFIXES):
        return "'" + memo
    return memo
