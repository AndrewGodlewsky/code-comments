"""Submit card charges to the payments API."""

import json


class ChargeFailed(Exception):
    """The charge was not captured, or its outcome is unknown."""


def submit_charge(conn, amount_cents, card_token):
    """Charge a single-use card token; return the charge id."""
    return _post_charge(conn, {"amount": amount_cents, "source": card_token})


def renew_subscription(conn, amount_cents, customer_id):
    """Charge a customer's saved card for a subscription renewal; return the charge id.

    Raises ChargeFailed when the charge is declined, held, or its outcome is
    unknown; the renewal worker flags those for the billing team.
    """
    return _post_charge(conn, {"amount": amount_cents, "customer": customer_id})


def _post_charge(conn, payload):
    body = json.dumps(payload)
    # Never retry here, even on the renewal worker's flaky pooled connections:
    # the charges API has no idempotency keys, so resending after a reset can
    # charge the card twice if the first request landed. A reset becomes
    # ChargeFailed ("payment status unknown") and support reconciles it.
    try:
        response = conn.post("/charges", body)
    except ConnectionResetError as error:
        raise ChargeFailed("connection reset; charge status unknown") from error
    # 202 means the charge was queued for fraud review, not captured, so only
    # 201 counts as success here.
    if response["status"] != 201:
        raise ChargeFailed(response.get("error", "unknown error"))
    return response["charge_id"]
