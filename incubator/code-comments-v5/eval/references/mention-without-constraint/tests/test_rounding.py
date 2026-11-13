import unittest
from decimal import Decimal

from pricing.rounding import round_price


class RoundPriceTest(unittest.TestCase):
    def test_halves_round_up(self):
        self.assertEqual(round_price(Decimal("2.345")), Decimal("2.35"))

    def test_rounds_down_below_half(self):
        self.assertEqual(round_price(Decimal("2.344")), Decimal("2.34"))

    def test_chf_rounds_to_five_rappen(self):
        self.assertEqual(round_price(Decimal("1.03"), "CHF"), Decimal("1.05"))
        self.assertEqual(round_price(Decimal("1.02"), "CHF"), Decimal("1.00"))


if __name__ == "__main__":
    unittest.main()
