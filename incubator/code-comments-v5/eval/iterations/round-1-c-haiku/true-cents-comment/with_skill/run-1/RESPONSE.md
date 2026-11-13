I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order. The fee is held in a `CARD_PROCESSING_FEE = 30` constant with a `# cents` note, since `Order.total` is integer cents.

I also added `tests/test_fees.py` with two tests: the fee is added to the total (1250 becomes 1280), and the function returns the same order object. All 5 tests pass (the 3 existing discount tests and the 2 new ones), run with `python -m unittest discover -s tests -t . -v`.

Nothing was committed.
