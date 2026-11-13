import unittest

from orders.fees import add_card_fee
from orders.model import Order


class CardFeeOnIntegerCentTotalsTest(unittest.TestCase):
    def test_adds_thirty_cents_to_a_round_total(self):
        order = add_card_fee(Order("H-1", 1000))
        self.assertIs(type(order.total), int)
        self.assertEqual(order.total, 1030)

    def test_adds_thirty_cents_to_an_odd_total(self):
        self.assertEqual(add_card_fee(Order("H-2", 1999)).total, 2029)

    def test_adds_thirty_cents_to_an_empty_total(self):
        self.assertEqual(add_card_fee(Order("H-3", 0)).total, 30)


if __name__ == "__main__":
    unittest.main()
