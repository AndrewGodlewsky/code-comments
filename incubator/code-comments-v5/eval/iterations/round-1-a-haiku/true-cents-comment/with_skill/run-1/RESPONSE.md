I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order. `Order.total` is in integer cents (per `orders/model.py`), so the fee is stored as `CARD_FEE_CENTS = 30` and added directly.

I did not add a test for it, since you did not ask for one. I also did not add a comment explaining why the fee is 30 cents, because the repository does not say where that figure comes from. If you can tell me the reason (for example, the card processor's rate or a pricing decision), I can record it beside the constant.
