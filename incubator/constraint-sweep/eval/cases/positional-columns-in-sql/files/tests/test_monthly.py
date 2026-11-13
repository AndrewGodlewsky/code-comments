import os
import tempfile
import unittest
from decimal import Decimal

from exporter.csv_out import write_csv
from exporter.rows import Entry
from reports.monthly import monthly_totals


class MonthlyTotalsTest(unittest.TestCase):
    def test_sums_each_account_over_the_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for day, amount in (("01", "12.50"), ("02", "7.50")):
                path = os.path.join(tmp, f"ledger-{day}.csv")
                with open(path, "w", newline="", encoding="utf-8") as fh:
                    write_csv([Entry(f"E-{day}", "4000", amount, "EUR", f"2026-11-{day}T09:00:00Z")], fh)
                paths.append(path)
            self.assertEqual(monthly_totals(paths), {"4000": Decimal("20.00")})


if __name__ == "__main__":
    unittest.main()
