I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The fee is stored as `CARD_PROCESSING_FEE_CENTS = 30`, and `Order.total` is in integer cents (documented in `orders/model.py:9`), so the addition is in the same units. I checked that against `apply_discount` in `orders/discounts.py`, which also works in integer cents, and I did not change any existing code.

Checks:
- The existing test suite still passes (3 tests).
- A quick probe on an order with total 1250 returned 1280.

No false claims about existing code came up, so I made no corrections to comments or docs.
