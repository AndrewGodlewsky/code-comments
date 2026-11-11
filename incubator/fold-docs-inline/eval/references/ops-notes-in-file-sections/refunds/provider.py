"""Sends approved refunds to the payment provider."""


class ProviderError(Exception):
    """The provider refused the refund."""


def send_refund(session, refund):
    # The provider refuses a second refund with the same idempotency key, so keying on
    # the refund's own id means a retried call never pays out twice.
    response = session.post(
        "/v2/refunds",
        json={"payment": refund["payment_id"], "amount": str(refund["amount"])},
        headers={"Idempotency-Key": refund["id"]},
    )
    if response["status"] != "accepted":
        raise ProviderError(response.get("reason", "unknown"))
    return response["refund_id"]
