"""Apply payment events to an in-memory account ledger."""


class Ledger:
    def __init__(self):
        self.balances = {}

    def apply(self, event):
        account = event["account"]
        self.balances[account] = self.balances.get(account, 0) + event["amount_cents"]
        return self.balances[account]
