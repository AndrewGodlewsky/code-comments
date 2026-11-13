I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order. The fee is held in a module constant, `CARD_FEE_CENTS = 30`, and the total is in integer cents, as `orders/model.py` documents.

I checked it with a quick call (a 1250-cent order becomes 1280) and the existing tests still pass (3 tests, OK). I did not add tests for the new function.

Two things to confirm:
- Your request gave the fee amount but not the reason for it or where it comes from, so the code does not record either. If the fee has a source, such as a payment-provider price sheet or a finance decision, tell me and I will add it beside the constant.
- The function adds the fee unconditionally. If the fee should apply only to card payments, or only to some orders, tell me the rule and I will add that check.
