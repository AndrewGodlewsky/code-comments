import unittest
from decimal import Decimal

from orders.fees import add_card_fee
from orders.model import Order


class CardFeeOnDecimalDollarTotalsTest(unittest.TestCase):
    def test_adds_thirty_cents_to_a_round_total(self):
        order = add_card_fee(Order("H-1", Decimal("10.00")))
        self.assertIsInstance(order.total, Decimal)
        self.assertEqual(order.total, Decimal("10.30"))

    def test_adds_thirty_cents_to_an_odd_total(self):
        self.assertEqual(add_card_fee(Order("H-2", Decimal("19.99"))).total, Decimal("20.29"))

    def test_adds_thirty_cents_to_an_empty_total(self):
        self.assertEqual(add_card_fee(Order("H-3", Decimal("0.00"))).total, Decimal("0.30"))


if __name__ == "__main__":
    unittest.main()
