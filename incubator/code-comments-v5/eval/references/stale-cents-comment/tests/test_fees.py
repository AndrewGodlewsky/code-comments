import unittest
from decimal import Decimal

from orders.fees import add_card_fee
from orders.model import Order


class AddCardFeeTest(unittest.TestCase):
    def test_adds_thirty_cents(self):
        order = add_card_fee(Order("A-2001", Decimal("12.50")))
        self.assertEqual(order.total, Decimal("12.80"))


if __name__ == "__main__":
    unittest.main()
