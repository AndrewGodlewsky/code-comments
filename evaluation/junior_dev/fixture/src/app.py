"""shopfront: place orders, check stock, charge the card, store the order."""

import json
from pathlib import Path

from .payments import charge

ORDERS = Path(__file__).resolve().parents[1] / "data" / "orders.json"
STOCK = {"mug": 12, "shirt": 3, "poster": 0}
PRICES = {"mug": 900, "shirt": 2500, "poster": 1500}


def total(items):
    return sum(PRICES[name] * qty for name, qty in items.items())


def place_order(customer, items, card_token):
    for name, qty in items.items():
        if STOCK.get(name, 0) < qty:
            return {"status": "rejected", "reason": f"out of stock: {name}"}
    payment = charge(card_token, total(items))
    if not payment["ok"]:
        return {"status": "rejected", "reason": "payment failed"}
    for name, qty in items.items():
        STOCK[name] -= qty
    orders = json.loads(ORDERS.read_text()) if ORDERS.exists() else []
    order = {"id": len(orders) + 1, "customer": customer, "items": items, "payment": payment["id"]}
    orders.append(order)
    ORDERS.write_text(json.dumps(orders, indent=1))
    return {"status": "placed", "order": order}
