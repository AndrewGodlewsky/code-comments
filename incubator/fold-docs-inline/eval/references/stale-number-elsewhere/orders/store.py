"""The warehouse's copy of shop orders."""


class OrderStore:
    """Orders keyed by the shop's order id."""

    def __init__(self):
        self.rows = {}

    def upsert(self, order):
        self.rows[order["id"]] = dict(order)
