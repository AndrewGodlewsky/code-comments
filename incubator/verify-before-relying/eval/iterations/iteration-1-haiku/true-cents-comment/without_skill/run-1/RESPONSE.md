I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order object.

Order totals are integer cents (see `orders/model.py`), so the fee is stored as the integer `30` in a named constant, `CARD_PROCESSING_FEE`, and added directly with no float conversion.

I also added `tests/test_fees.py` with two tests: one checks that 1250 becomes 1280, and one checks that the function returns the same order instance. All 5 tests pass (the 3 existing discount tests and the 2 new ones), run with `python -m unittest discover -s tests -t . -v`.

Nothing else in the repository was changed.
