import unittest
from decimal import Decimal

from invoices.lines import InvoiceLine
from invoices.total import invoice_total


class InvoiceTotalTest(unittest.TestCase):
    def test_sums_quantity_times_price(self):
        lines = [InvoiceLine("Widget", 2, Decimal("2.50")), InvoiceLine("Bolt", 5, Decimal("0.25"))]
        self.assertEqual(invoice_total(lines), Decimal("6.25"))

    def test_an_empty_invoice_is_zero(self):
        self.assertEqual(invoice_total([]), Decimal("0"))


if __name__ == "__main__":
    unittest.main()
