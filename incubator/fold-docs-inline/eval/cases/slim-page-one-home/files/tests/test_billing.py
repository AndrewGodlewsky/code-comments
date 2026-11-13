import unittest
from decimal import Decimal

from billing.lines import Line, invoice_lines
from billing.totals import invoice_total


class BillingTest(unittest.TestCase):
    def test_total_rounds_half_up(self):
        lines = [Line("a", "x", Decimal("0.125"))]
        self.assertEqual(invoice_total(lines), Decimal("0.13"))

    def test_lines_come_back_in_sku_order(self):
        order = {"items": [{"sku": "B2", "description": "bolt", "amount": "1.00"},
                           {"sku": "A1", "description": "nut", "amount": "0.50"}]}
        self.assertEqual([line.sku for line in invoice_lines(order)], ["A1", "B2"])


if __name__ == "__main__":
    unittest.main()
