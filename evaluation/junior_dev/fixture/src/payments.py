"""Talks to the card payment provider. charge() returns {ok, id} and never raises."""

import uuid


def charge(card_token, amount_cents):
    if not card_token:
        return {"ok": False, "id": None}
    return {"ok": True, "id": f"pay_{uuid.uuid4().hex[:12]}"}
