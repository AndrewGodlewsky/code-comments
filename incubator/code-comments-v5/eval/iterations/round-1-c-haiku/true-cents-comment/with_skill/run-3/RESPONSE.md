I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The fee is stored as `CARD_FEE_CENTS = 30`, with a comment that it is in integer cents, matching the `Order.total` comment in `orders/model.py`. I did not add a test file, since the request asked only for the function.

No evidence in the repository explains why the fee is 30 cents or whether it applies to every card order. I recorded only the value, so if there is a reason or a rule (for example a minimum order or a card type exemption), please share it so the comment can state it.
