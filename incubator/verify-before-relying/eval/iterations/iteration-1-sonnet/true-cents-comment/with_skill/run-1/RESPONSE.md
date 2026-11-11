I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The fee is stored as `CARD_PROCESSING_FEE = 30`, in cents. The only claim I relied on was that the order total is in integer cents. `orders/model.py:9` says so ("amount due, in integer cents"). The tests (`tests/test_discounts.py`) and `apply_discount` in `orders/discounts.py` treat totals as cents too (1250 becomes 1000 after 20% off). That claim checks out, so I left it as written and added no conversion.

I didn't add a test for the fee or run anything.
