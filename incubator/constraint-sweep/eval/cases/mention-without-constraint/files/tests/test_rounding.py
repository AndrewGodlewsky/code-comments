import unittest
from decimal import Decimal

from pricing.rounding import round_price


class RoundPriceTest(unittest.TestCase):
    def test_halves_round_up(self):
        self.assertEqual(round_price(Decimal("2.345")), Decimal("2.35"))

    def test_rounds_down_below_half(self):
        self.assertEqual(round_price(Decimal("2.344")), Decimal("2.34"))


if __name__ == "__main__":
    unittest.main()
