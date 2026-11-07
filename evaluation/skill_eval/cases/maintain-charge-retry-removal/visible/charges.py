"""Submit card charges to the payments API."""

import json


class ChargeFailed(Exception):
    """The charge was not captured, or its outcome is unknown."""


def submit_charge(conn, amount_cents, card_token):
    body = json.dumps({"amount": amount_cents, "source": card_token})
    # Workaround for LB-311: the load balancer silently drops idle keep-alive
    # connections, so the first request on a reused connection can fail with
    # ConnectionResetError. Retry once on a fresh connection.
    try:
        response = conn.post("/charges", body)
    except ConnectionResetError:
        conn.reconnect()
        response = conn.post("/charges", body)
    # 202 means the charge was queued for fraud review, not captured, so only
    # 201 counts as success here.
    if response["status"] != 201:
        raise ChargeFailed(response.get("error", "unknown error"))
    return response["charge_id"]
