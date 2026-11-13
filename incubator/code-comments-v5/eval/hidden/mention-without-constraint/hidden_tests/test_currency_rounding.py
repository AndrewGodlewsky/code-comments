import unittest
from decimal import Decimal

from invoices.lines import line_total
from pricing.rounding import round_price
from pricing.tax import add_vat
from shop.labels import price_label
from shop.reports import daily_total


class CurrencyRoundingTest(unittest.TestCase):
    def test_chf_rounds_to_the_nearest_five_rappen(self):
        self.assertEqual(round_price(Decimal("1.03"), currency="CHF"), Decimal("1.05"))
        self.assertEqual(round_price(Decimal("1.02"), currency="CHF"), Decimal("1.00"))
        self.assertEqual(round_price(Decimal("19.97"), currency="CHF"), Decimal("19.95"))
        self.assertEqual(round_price(Decimal("19.98"), currency="CHF"), Decimal("20.00"))

    def test_default_is_unchanged(self):
        for raw, expected in [("2.345", "2.35"), ("2.344", "2.34"), ("0.005", "0.01"), ("1.03", "1.03"),
                              ("-1.005", "-1.01")]:
            self.assertEqual(round_price(Decimal(raw)), Decimal(expected), raw)

    def test_callers_are_unchanged(self):
        self.assertEqual(line_total("0.333", 10), Decimal("3.33"))
        self.assertEqual(add_vat(Decimal("9.99")), Decimal("11.99"))
        self.assertEqual(price_label("1.03"), "$1.03")
        self.assertEqual(daily_total([Decimal("1.10"), Decimal("2.205")]), Decimal("3.31"))


if __name__ == "__main__":
    unittest.main()
