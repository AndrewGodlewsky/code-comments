"""The weekly payout run."""
from events.handlers import handle_payout
from events.money import pence


def run_payouts(merchants):
    """Return the postings that pay every merchant with a positive balance."""
    postings = []
    for merchant in merchants:
        if pence(merchant["balance"]) > 0:
            postings += handle_payout({"kind": "payout", "amount": merchant["balance"]})
    return postings
