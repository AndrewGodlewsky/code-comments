I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order.

Order totals are integer cents (see `orders/model.py`), so the fee is stored as `CARD_PROCESSING_FEE = 30` and added directly, with no conversion. For example, an order with a total of 1250 becomes 1280.

I checked this with a quick run that added the fee to a 1250-cent order and got 1280 back. I did not add a unit test file or run the existing test suite.
