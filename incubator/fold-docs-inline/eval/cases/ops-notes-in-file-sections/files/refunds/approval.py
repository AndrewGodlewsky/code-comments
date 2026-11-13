"""Who has to approve a refund before it is sent."""

from decimal import Decimal

SECOND_APPROVER_THRESHOLD = Decimal("500")


def needs_second_approver(amount):
    return amount >= SECOND_APPROVER_THRESHOLD


def can_send(refund):
    """True when the refund has every approval it needs."""
    needed = 2 if needs_second_approver(refund["amount"]) else 1
    return len(set(refund["approvers"])) >= needed
