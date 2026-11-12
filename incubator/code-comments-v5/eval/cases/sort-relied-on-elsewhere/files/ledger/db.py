"""Ledger database access.

Entries are append-only: the bank feed inserts each one as it clears.
"""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id TEXT PRIMARY KEY,
    account TEXT NOT NULL,
    amount_pence INTEGER NOT NULL,
    memo TEXT NOT NULL DEFAULT ''
)
"""


def connect(path=":memory:"):
    """Open the ledger database, creating the entries table if needed."""
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA)
    return conn


def add_entries(conn, entries):
    """Insert (id, account, amount_pence, memo) tuples."""
    conn.executemany("INSERT INTO entries (id, account, amount_pence, memo) VALUES (?, ?, ?, ?)", entries)
    conn.commit()
