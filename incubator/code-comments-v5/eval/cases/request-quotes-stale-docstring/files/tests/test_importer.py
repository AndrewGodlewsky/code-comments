import io
import unittest
from datetime import date

from deliveries.importer import read_orders


class ReadOrdersTest(unittest.TestCase):
    def test_leaves_out_undated_rows_and_lists_dates_that_do_not_exist(self):
        sheet = io.StringIO("order_id,ordered\nA1,2026-03-14\nA2,tbc\nA3,31/02/2026\nA4,14/03/2026\n")
        orders, skipped = read_orders(sheet)
        self.assertEqual(orders, {"A1": date(2026, 3, 14), "A4": date(2026, 3, 14)})
        self.assertEqual(skipped, [4])


if __name__ == "__main__":
    unittest.main()
