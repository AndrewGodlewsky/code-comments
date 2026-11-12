import unittest
from decimal import Decimal

from invoices.lines import InvoiceLine
from invoices.total import invoice_total


def total(*lines):
    return invoice_total([InvoiceLine("item", quantity, Decimal(price)) for quantity, price in lines])


class InvoiceTotalRoundsHalfUpTest(unittest.TestCase):
    def test_a_half_cent_rounds_up(self):
        self.assertEqual(total((1, "0.125")), Decimal("0.13"))

    def test_a_half_cent_above_an_even_cent_rounds_up(self):
        self.assertEqual(total((3, "1.335")), Decimal("4.01"))  # 4.005

    def test_the_sum_of_several_lines_is_rounded(self):
        self.assertEqual(total((2, "0.0625"), (1, "1.00")), Decimal("1.13"))  # 1.125

    def test_other_amounts_round_to_the_nearest_cent(self):
        self.assertEqual(total((1, "1.234")), Decimal("1.23"))
        self.assertEqual(total((1, "1.236")), Decimal("1.24"))

    def test_the_total_has_two_decimal_places(self):
        self.assertEqual(total((2, "2.5")).as_tuple().exponent, -2)


if __name__ == "__main__":
    unittest.main()
