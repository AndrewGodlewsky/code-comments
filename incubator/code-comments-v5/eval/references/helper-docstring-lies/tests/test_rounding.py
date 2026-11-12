import unittest
from decimal import Decimal

from money.rounding import round_cents


class RoundCentsTest(unittest.TestCase):
    def test_rounds_to_two_places(self):
        self.assertEqual(round_cents(Decimal("1.234")), Decimal("1.23"))
        self.assertEqual(round_cents(Decimal("1.236")), Decimal("1.24"))

    def test_halves_go_to_the_even_cent(self):
        # The ledger has to agree with the bank statement to the cent, and the bank
        # rounds halves to the even cent.
        self.assertEqual(round_cents(Decimal("0.125")), Decimal("0.12"))
        self.assertEqual(round_cents(Decimal("0.135")), Decimal("0.14"))


if __name__ == "__main__":
    unittest.main()
