"""Handlers for payment events.

Each handler takes an event dict and returns the ledger postings it produces, as
(account, pence) pairs that sum to zero.
"""
from events.money import pence

# The card network's fixed fee for each chargeback, in pence.
CHARGEBACK_FEE = 1500


def handle_refund(event):
    """Reverse a refunded payment."""
    amount = pence(event["amount"])
    return [("refunds", amount), ("cash", -amount)]


def handle_chargeback(event):
    """Post a chargeback and the network's fee for it."""
    amount = pence(event["amount"])
    return [("chargebacks", amount), ("fees", CHARGEBACK_FEE), ("cash", -amount - CHARGEBACK_FEE)]


def handle_payout(event):
    """Pay a merchant's balance out of cash."""
    amount = pence(event["amount"])
    return [("payouts", amount), ("cash", -amount)]
