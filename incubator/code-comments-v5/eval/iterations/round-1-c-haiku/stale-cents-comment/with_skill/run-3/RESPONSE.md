I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The fee is `Decimal("0.30")`. I used a Decimal because the existing tests build orders with Decimal dollar amounts such as `Decimal("12.50")`.

One correction was needed. The comment on `Order.total` in `orders/model.py` said "amount due, in integer cents". The tests show the total is a Decimal in dollars, so I changed the comment to "amount due, a Decimal in dollars". If the total really is meant to be integer cents, the fee constant and the comment both need to change together, so please confirm which unit is correct.

I checked that `add_card_fee` on an order of `Decimal("12.50")` gives `12.80`, and the existing three tests still pass. I did not add a test for the new function.
