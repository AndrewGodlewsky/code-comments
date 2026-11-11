I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

Before relying on it, I checked the comment in `orders/model.py`, in `Order.__init__`, that says `total` is "amount due, in integer cents". The tests back it up: in `tests/test_discounts.py`, 1250 becomes 1000 after a 20% discount, and `apply_discount` uses integer floor division. The claim holds, so I left it as written. The fee is the integer `30` (`CARD_FEE_CENTS`), with no unit conversion.

I did not add tests for the new function or run any tests.
