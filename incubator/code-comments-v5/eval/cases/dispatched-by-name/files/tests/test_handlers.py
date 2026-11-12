import unittest

from events.handlers import handle_refund
from payouts.batch import run_payouts


class HandlersTest(unittest.TestCase):
    def test_refund_reverses_the_payment(self):
        self.assertEqual(handle_refund({"kind": "refund", "amount": "12.50"}),
                         [("refunds", 1250), ("cash", -1250)])

    def test_payout_run_skips_empty_balances(self):
        postings = run_payouts([{"id": "m1", "balance": "40.00"}, {"id": "m2", "balance": "0"}])
        self.assertEqual(postings, [("payouts", 4000), ("cash", -4000)])


if __name__ == "__main__":
    unittest.main()
