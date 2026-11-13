I added `add_card_fee(order)` in `orders/fees.py`. It adds a 30-cent fee to `order.total` and returns the order. I did not run anything, and I did not add tests.

**Units conflict.** The comment on `Order.total` in `orders/model.py` said "amount due, in integer cents". The existing tests in `tests/test_discounts.py` build orders with `Decimal` dollar amounts such as `Decimal("12.50")`. `apply_discount` also uses `/`, which would turn integer cents into floats.

I treated the tests as the real contract. The fee is `Decimal("0.30")` and I changed the model comment to "amount due, a Decimal in dollars".

If totals really are integer cents somewhere in production, the fee should be `30` and the model comment should go back. Please confirm which unit is right.

I put no reason for the fee in a comment, because nothing I had says why it is 30 cents. If a ticket or vendor rate record it, I can add a pointer.
