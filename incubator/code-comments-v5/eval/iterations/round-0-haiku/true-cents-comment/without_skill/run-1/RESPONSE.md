I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order object.

Order totals are integer cents (per `orders/model.py`), so the fee is the constant `CARD_PROCESSING_FEE_CENTS = 30` added directly to the total.

I also added `tests/test_fees.py` with two tests: the total goes up by 30 cents, and the function returns the same order. Running `python -m unittest tests.test_fees tests.test_discounts` passes all 5 tests.
