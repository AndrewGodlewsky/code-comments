import unittest

from payments.model import payment


class PaymentTest(unittest.TestCase):
    def test_currency_defaults_to_gbp(self):
        self.assertEqual(payment("2026-11-01", "ACME Ltd", "12.50", "INV-1")["currency"], "GBP")


if __name__ == "__main__":
    unittest.main()
