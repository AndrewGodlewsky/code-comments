import unittest

from orders.fees import add_card_fee
from orders.model import Order


class AddCardFeeTest(unittest.TestCase):
    def test_adds_thirty_cents(self):
        order = add_card_fee(Order("A-2001", 1250))
        self.assertEqual(order.total, 1280)


if __name__ == "__main__":
    unittest.main()
