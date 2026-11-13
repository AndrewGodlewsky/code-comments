I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order. The fee is held in a `CARD_PROCESSING_FEE_CENTS = 30` constant, and `Order.total` is in integer cents, so the fee is added in the same unit.

I checked it with a quick run: an order at 1000 cents came back at 1030. I did not add a unit test for it, since you did not ask for one. The existing tests were not run.

No reason for the fee was given in the request, so the module records only the value.
