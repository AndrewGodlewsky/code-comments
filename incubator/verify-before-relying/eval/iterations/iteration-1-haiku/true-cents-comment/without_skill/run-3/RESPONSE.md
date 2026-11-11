I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order object.

`Order.total` is stored in integer cents (per `orders/model.py`), so the fee is held as `CARD_PROCESSING_FEE_CENTS = 30` and added directly. For example, an order with a total of 1250 becomes 1280.

I checked it with a quick script: the total went from 1250 to 1280 and the returned object is the same instance. The existing test suite still passes (3 tests). I did not add a test file for the new function.

One thing to confirm: the fee is applied each time the function is called, so calling it twice on the same order adds 60 cents. If checkout can call it more than once, it may need a guard.
