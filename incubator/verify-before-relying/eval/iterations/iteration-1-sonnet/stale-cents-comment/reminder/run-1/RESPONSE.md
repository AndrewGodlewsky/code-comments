I added `add_card_fee(order)` in `orders/fees.py`, with tests in `tests/test_fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order. The tests pass.

**Comment correction:** the comment on `Order.total` in `orders/model.py` said the total is in "integer cents". That is wrong. The existing discount tests build orders with `Decimal` dollar amounts (for example `Decimal("12.50")`), and `apply_discount` works on that basis. If I had trusted the comment, I would have added `30` and made every total $29.70 too high. The fee is therefore `Decimal("0.30")`. I changed the comment to say the total is a Decimal in dollars.

There was no conflict with a stated requirement. The 30-cent fee is kept exactly as you gave it.

Nothing stops `add_card_fee` being applied twice to the same order, so the caller has to make sure it runs only once.
