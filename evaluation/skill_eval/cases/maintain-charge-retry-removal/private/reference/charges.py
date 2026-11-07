"""Submit card charges to the payments API."""

import json


class ChargeFailed(Exception):
    """The charge was not captured, or its outcome is unknown."""


def submit_charge(conn, amount_cents, card_token):
    body = json.dumps({"amount": amount_cents, "source": card_token})
    # Never retry here: the charges API has no idempotency keys, so resending
    # after a reset can charge the card twice if the first request landed.
    try:
        response = conn.post("/charges", body)
    except ConnectionResetError as error:
        raise ChargeFailed("connection reset; charge status unknown") from error
    # 202 means the charge was queued for fraud review, not captured, so only
    # 201 counts as success here.
    if response["status"] != 201:
        raise ChargeFailed(response.get("error", "unknown error"))
    return response["charge_id"]
