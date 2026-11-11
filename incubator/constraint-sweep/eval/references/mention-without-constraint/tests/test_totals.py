import unittest
from decimal import Decimal

from invoices.lines import line_total
from pricing.tax import add_vat
from shop.labels import price_label
from shop.reports import daily_total


class TotalsTest(unittest.TestCase):
    def test_line_is_rounded_once(self):
        self.assertEqual(line_total("0.333", 10), Decimal("3.33"))

    def test_totals_round_to_the_cent(self):
        self.assertEqual(daily_total([Decimal("1.10"), Decimal("2.205")]), Decimal("3.31"))

    def test_vat_and_label(self):
        self.assertEqual(add_vat(Decimal("10.00")), Decimal("12.00"))
        self.assertEqual(price_label("1234.5"), "$1,234.50")


if __name__ == "__main__":
    unittest.main()
