import unittest

from ledger.db import add_entries, connect
from ledger.rows import fetch_rows


class FetchRowsTest(unittest.TestCase):
    def test_returns_every_entry(self):
        conn = connect()
        add_entries(conn, [("E-0003", "4000", 500, "rent"), ("E-0001", "4100", 120, "coffee"),
                           ("E-0002", "4100", 75, "")])
        self.assertEqual({row.id for row in fetch_rows(conn)}, {"E-0001", "E-0002", "E-0003"})

    def test_amounts_are_pence(self):
        conn = connect()
        add_entries(conn, [("E-0009", "4000", 1999, "fee")])
        self.assertEqual(fetch_rows(conn)[0].amount_pence, 1999)


if __name__ == "__main__":
    unittest.main()
