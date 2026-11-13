I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee (`CARD_FEE_CENTS = 30`) to `order.total` and returns the same order. Totals are integer cents, as documented on `Order`, so the fee is added in cents.

Before relying on the existing code, I checked the docstrings and comments against the code and tests:
- `Order.total` is documented as "amount due, in integer cents". `apply_discount` works in integer cents, so this matches.
- `apply_discount`'s docstring ("Take percent (0 to 100) off the order total and return the order") matches its range check and its tests.

I found no wrong descriptions, so I changed nothing in the existing code. There is no conflict between your requirement and the code.

I also added `tests/test_fees.py` with two tests: the total goes up by 30 (1250 becomes 1280), and the same order object is returned. `python -m unittest` runs all 5 tests, and they pass.
