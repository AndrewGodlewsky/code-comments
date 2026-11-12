I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order. The total is in integer cents, as `orders/model.py` documents, so the fee is stored as `CARD_PROCESSING_FEE_CENTS = 30` and the function docstring says the total is in cents.

I also added `tests/test_fees.py` with two tests, following the style of `tests/test_discounts.py`. One checks that a 1250 total becomes 1280. The other checks that the same order object is returned. All 5 tests pass with `python -m unittest discover -s tests -t .`.

Two things to know:
- The function is not idempotent. Calling it twice on the same order adds the fee twice. Your request did not say whether that should be guarded against, so I left it as written.
- I did not commit anything, since this is a self-contained exercise with no git.
