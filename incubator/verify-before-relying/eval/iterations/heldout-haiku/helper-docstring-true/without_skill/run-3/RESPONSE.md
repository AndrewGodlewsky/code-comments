I changed `invoice_total` in `invoices/total.py` so the invoice total is rounded half up to the cent. It now sums quantity times unit price as before, then passes the result through `round_cents` from `money/rounding.py`, which already rounds half up with `ROUND_HALF_UP`.

I also updated the function's docstring to mention the rounding, and added a test in `tests/test_total.py` for a line that totals 0.125, which now returns 0.13.

I ran the unit tests in the repository and they pass.
