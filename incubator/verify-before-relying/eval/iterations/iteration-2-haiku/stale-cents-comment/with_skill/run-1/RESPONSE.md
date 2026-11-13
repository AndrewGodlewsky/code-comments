I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order. I also added `tests/test_fees.py` with two tests, and all five tests in the repository pass.

The premise in the `Order` comment was wrong. `orders/model.py` said `total` is "amount due, in integer cents". The existing tests in `tests/test_discounts.py` pin `total` as dollars in a `Decimal` (for example `Decimal("12.50")` discounted by 20% gives `Decimal("10.00")`). I also ran a probe: an integer total of 1250 discounted by 20% gives 1000.0 as a float, so the cents reading does not hold in the code either. I built the fee on the real behaviour: `CARD_FEE = Decimal("0.30")`, added directly to the total, so it is 30 cents in the dollar units the tests use.

I corrected the comment in place in `orders/model.py` to "amount due, in dollars as a Decimal". No other existing code was changed.
