I changed `invoice_total` in `invoices/total.py` so it now rounds the summed total with `round_cents` from `money/rounding.py`. That helper quantizes to the cent with `ROUND_HALF_UP`, so 0.125 becomes 0.13 and 0.135 becomes 0.14. The function's docstring now says the total is rounded to the cent, half up, as the tax office requires.

I ran the existing tests (4 tests, all passing) and spot-checked the rounding by hand. I did not add a dedicated invoice rounding test; say if you want one.
