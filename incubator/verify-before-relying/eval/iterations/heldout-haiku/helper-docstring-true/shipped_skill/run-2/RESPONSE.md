I changed `invoice_total` in `invoices/total.py` so it returns `round_cents(...)` applied to the summed total. Rounding uses `money/rounding.py`, which rounds half up to the cent. Rounding applies to the invoice total, not to each line.

The docstring now says the total is rounded half up to the cent and that the tax office requires it.

I also added `test_total_rounds_half_up_to_the_cent` to `tests/test_total.py`. It checks that a single line of 0.125 gives 0.13. All 5 tests pass (`python -m unittest discover -s tests -t .`).
