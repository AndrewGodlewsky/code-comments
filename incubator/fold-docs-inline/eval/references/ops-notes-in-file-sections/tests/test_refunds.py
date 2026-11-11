import unittest
from decimal import Decimal

from refunds.approval import can_send, needs_second_approver
from refunds.provider import ProviderError, send_refund


class Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, path, json, headers):
        self.calls.append((path, json, headers))
        return self.response


REFUND = {"id": "r-1", "payment_id": "p-9", "amount": Decimal("20.00"), "approvers": ["kim"]}


class ApprovalTest(unittest.TestCase):
    def test_large_refunds_need_two_people(self):
        self.assertTrue(needs_second_approver(Decimal("500")))
        self.assertFalse(needs_second_approver(Decimal("499.99")))
        self.assertFalse(can_send(dict(REFUND, amount=Decimal("600"))))
        self.assertTrue(can_send(dict(REFUND, amount=Decimal("600"), approvers=["kim", "lee"])))


class ProviderTest(unittest.TestCase):
    def test_returns_the_provider_id(self):
        session = Session({"status": "accepted", "refund_id": "pr-5"})
        self.assertEqual(send_refund(session, REFUND), "pr-5")
        self.assertEqual(session.calls[0][2], {"Idempotency-Key": "r-1"})

    def test_raises_on_refusal(self):
        with self.assertRaises(ProviderError):
            send_refund(Session({"status": "refused", "reason": "closed"}), REFUND)


if __name__ == "__main__":
    unittest.main()
