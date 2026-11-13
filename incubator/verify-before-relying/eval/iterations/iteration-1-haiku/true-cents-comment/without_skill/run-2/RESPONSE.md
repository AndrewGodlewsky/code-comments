I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

Order totals are integer cents (see `orders/model.py`), so the fee is stored as `CARD_PROCESSING_FEE_CENTS = 30` and added directly. For example, a 1250-cent order becomes 1280.

I checked it with a quick run (a 1250-cent order gave 1280) and the existing three unit tests still pass. I did not add a test file for the fee, so say if you want one.
