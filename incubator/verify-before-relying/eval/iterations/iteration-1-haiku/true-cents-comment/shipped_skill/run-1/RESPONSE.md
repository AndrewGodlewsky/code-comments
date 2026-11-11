I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order. The fee is a module constant, `CARD_FEE_CENTS = 30`, and the total is in integer cents, matching `Order`.

I also added `tests/test_fees.py` with two tests: the total goes up by 30, and the same order object is returned. All 5 tests pass (`python -m unittest discover -s tests -t . -v`), including the existing discount tests.

Nothing else changed. The new module's docstring and the function docstring are short and do not repeat the code. No ticket or issue is recorded for the fee, so none is cited in the code.
