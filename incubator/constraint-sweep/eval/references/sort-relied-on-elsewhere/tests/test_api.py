import unittest

from ledger.api import balances
from ledger.db import add_entries, connect


class BalancesTest(unittest.TestCase):
    def test_totals_per_account_and_overall(self):
        conn = connect()
        add_entries(conn, [("E-0002", "4000", 500, ""), ("E-0001", "4100", 120, ""), ("E-0003", "4000", -75, "")])
        self.assertEqual(balances(conn), {"accounts": {"4000": 425, "4100": 120}, "total": 545})


if __name__ == "__main__":
    unittest.main()
