import unittest
from decimal import Decimal

from money.rounding import round_cents


class RoundCentsTest(unittest.TestCase):
    def test_rounds_to_two_places(self):
        self.assertEqual(round_cents(Decimal("1.234")), Decimal("1.23"))
        self.assertEqual(round_cents(Decimal("1.236")), Decimal("1.24"))

    def test_halves_round_up(self):
        # Finance rounds halves up everywhere, the ledger included.
        self.assertEqual(round_cents(Decimal("0.125")), Decimal("0.13"))
        self.assertEqual(round_cents(Decimal("0.135")), Decimal("0.14"))


if __name__ == "__main__":
    unittest.main()
