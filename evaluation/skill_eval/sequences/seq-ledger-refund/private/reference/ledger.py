"""Apply payment events to an in-memory account ledger."""


class Ledger:
    def __init__(self):
        self.balances = {}
        self.applied = set()

    def apply(self, event):
        # The payment gateway delivers webhooks at-least-once, so the same event
        # can arrive again hours later. Deduplicate on event_id rather than
        # account and amount: legitimate repeat payments share the same amount.
        return self._post(event, event["amount_cents"])

    def refund(self, event):
        # Refunds arrive through the same at-least-once webhook as payments, so
        # they are deduplicated on event_id in exactly the same way.
        return self._post(event, -event["amount_cents"])

    def _post(self, event, delta):
        account = event["account"]
        if event["event_id"] not in self.applied:
            self.applied.add(event["event_id"])
            self.balances[account] = self.balances.get(account, 0) + delta
        return self.balances.get(account, 0)
