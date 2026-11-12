I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order object.

Order totals are integer cents (see `orders/model.py`), so the fee is the integer `30` and no float conversion is needed. The fee is a module-level constant, `CARD_PROCESSING_FEE`, so it is defined in one place.

I did not add tests, since the request only asked for the function. I also did not run the test suite.
