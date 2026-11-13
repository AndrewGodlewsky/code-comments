I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order object.

Order totals are integer cents (see `orders/model.py`), so the fee is stored as `CARD_PROCESSING_FEE_CENTS = 30` and added directly. For example, an order with a total of 1250 becomes 1280. Calling the function again adds another 30 cents, so it should be called once per order.

I checked the behaviour with a quick script (1250 gives 1280, then 1310 on a second call) and the existing tests still pass (3 tests). I did not add a test file for the new function.
