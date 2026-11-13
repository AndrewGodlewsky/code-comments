"""Sends approved refunds to the payment provider."""


class ProviderError(Exception):
    """The provider refused the refund."""


def send_refund(session, refund):
    response = session.post(
        "/v2/refunds",
        json={"payment": refund["payment_id"], "amount": str(refund["amount"])},
        headers={"Idempotency-Key": refund["id"]},
    )
    if response["status"] != "accepted":
        raise ProviderError(response.get("reason", "unknown"))
    return response["refund_id"]
