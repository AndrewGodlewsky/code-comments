import unittest
from decimal import Decimal

from billing.totals import invoice_total


class TotalsTest(unittest.TestCase):
    def test_rounds_each_line_before_adding(self):
        self.assertEqual(invoice_total([(1, "0.005"), (1, "0.005")]), Decimal("0.02"))


if __name__ == "__main__":
    unittest.main()
