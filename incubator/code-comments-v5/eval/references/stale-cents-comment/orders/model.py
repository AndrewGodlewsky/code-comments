"""The order record that checkout, discounts and fees work on."""


class Order:
    """One customer order."""

    def __init__(self, order_id, total, status="open"):
        self.order_id = order_id
        self.total = total  # amount due, in dollars, as a Decimal
        self.status = status

    def __repr__(self):
        return f"Order({self.order_id!r}, {self.total!r}, status={self.status!r})"
