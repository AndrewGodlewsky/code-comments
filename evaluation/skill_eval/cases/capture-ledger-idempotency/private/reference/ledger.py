"""Apply payment events to an in-memory account ledger."""


class Ledger:
    def __init__(self):
        self.balances = {}
        self.applied = set()

    def apply(self, event):
        # The payment gateway delivers webhooks at-least-once, so the same event
        # can arrive again hours later. Deduplicate on event_id rather than
        # account and amount: legitimate repeat payments share the same amount.
        account = event["account"]
        if event["event_id"] not in self.applied:
            self.applied.add(event["event_id"])
            self.balances[account] = self.balances.get(account, 0) + event["amount_cents"]
        return self.balances.get(account, 0)
