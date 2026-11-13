I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The `Order` model in `orders/model.py` documents `total` as "amount due, in integer cents", so the fee is added as `CARD_PROCESSING_FEE_CENTS = 30` with no unit conversion.

I checked the existing claims the new code depends on. The `Order` comment on `total` matches how `apply_discount` uses it, and the existing tests (3) pass. I also ran `add_card_fee` once on a 1250-cent order and got 1280. I found no false claims in the code, so nothing was corrected.

I did not add a test for the new function, since the request asked only for the function.
