I changed `invoice_total` in `invoices/total.py` so it returns the sum of quantity times unit price rounded to the cent, half up, using `round_cents` from `money/rounding.py`.

The helper's docstring claim ("rounds to the nearest cent, rounding halves up") checked out. `tests/test_rounding.py::test_halves_round_up` pins 0.125 to 0.13 and 0.135 to 0.14, and the body uses `quantize` with `ROUND_HALF_UP`. I built on it as written and added no extra guard.

The old `invoice_total` docstring said the total was the plain sum, which is no longer true, so I corrected it to describe the rounding. Nothing else in the repository depends on that docstring.

I added `test_the_total_rounds_half_up_to_the_cent` to `tests/test_total.py` (one line of 0.125 gives 0.13). All 5 tests pass (`python -B -m unittest discover -s tests -t .`).

One assumption to check: `ROUND_HALF_UP` in Python's `Decimal` rounds ties away from zero. For negative totals, such as credit notes, that means -0.125 becomes -0.13. The tests do not cover negatives, and I did not change that behaviour. If the tax office means "toward positive infinity" for negative totals, that would need a change in `round_cents` and its tests.
