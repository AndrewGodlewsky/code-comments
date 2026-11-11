I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order. The fee is stored as `CARD_PROCESSING_FEE_CENTS = 30`, because `Order.total` is in integer cents.

I also added `tests/test_fees.py` with two tests: one checks that 1250 becomes 1280, and one checks that the same order object is returned. All 5 tests pass (`python -m unittest -v`), including the 3 existing discount tests.

Before relying on the existing code, I checked its comments and docstrings against the code and tests. They match: `Order.total` is documented as "amount due, in integer cents", and `apply_discount` does what its docstring says. I found no wrong descriptions, so I changed nothing in the existing files. There was no conflict between a stated requirement and the code.
