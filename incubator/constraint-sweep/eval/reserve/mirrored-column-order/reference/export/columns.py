"""Column order of the bank export.

The bank's import job reads columns by position; ingest/layout.json must list the
same columns in the same order.
"""

COLUMNS = ["date", "payee", "amount", "currency", "reference"]
