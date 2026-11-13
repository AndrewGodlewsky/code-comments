import unittest

from events.dispatch import dispatch


class ConfiguredRoutesTest(unittest.TestCase):
    def test_chargeback_reaches_its_handler(self):
        self.assertEqual(dispatch({"kind": "chargeback", "amount": "20.00"}),
                         [("chargebacks", 2000), ("fees", 1500), ("cash", -3500)])

    def test_refund_and_payout_still_route(self):
        self.assertEqual(dispatch({"kind": "refund", "amount": "5.00"}), [("refunds", 500), ("cash", -500)])
        self.assertEqual(dispatch({"kind": "payout", "amount": "7.25"}), [("payouts", 725), ("cash", -725)])


if __name__ == "__main__":
    unittest.main()
