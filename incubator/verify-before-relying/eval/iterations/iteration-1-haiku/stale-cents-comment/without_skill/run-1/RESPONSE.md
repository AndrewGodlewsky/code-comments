I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order, the same mutate-and-return pattern `apply_discount` uses.

One thing to check before relying on it: the comment in `orders/model.py` says `total` is "amount due, in integer cents", but the existing code and tests treat it as a `Decimal` amount in dollars (`Decimal("12.50")` is expected to come out as `Decimal("10.00")` after a 20% discount). I followed the code and tests, so the fee is `Decimal("0.30")` added to the total. If `total` really is integer cents, the fee should be `30` instead, and the `model.py` comment is correct. I did not change `model.py`, so the stale comment is still there for you to fix once you know which one is right.

I checked it with a quick run: a $12.50 order comes out at $12.80, and the existing three discount tests still pass.
