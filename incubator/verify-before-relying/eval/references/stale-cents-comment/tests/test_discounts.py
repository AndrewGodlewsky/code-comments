import unittest
from decimal import Decimal

from orders.discounts import apply_discount
from orders.model import Order


class ApplyDiscountTest(unittest.TestCase):
    def test_takes_the_percentage_off_the_total(self):
        order = apply_discount(Order("A-1001", Decimal("12.50")), 20)
        self.assertEqual(order.total, Decimal("10.00"))

    def test_zero_percent_leaves_the_total(self):
        order = apply_discount(Order("A-1002", Decimal("49.99")), 0)
        self.assertEqual(order.total, Decimal("49.99"))

    def test_rejects_a_percentage_over_100(self):
        with self.assertRaises(ValueError):
            apply_discount(Order("A-1003", Decimal("5.00")), 120)


if __name__ == "__main__":
    unittest.main()
