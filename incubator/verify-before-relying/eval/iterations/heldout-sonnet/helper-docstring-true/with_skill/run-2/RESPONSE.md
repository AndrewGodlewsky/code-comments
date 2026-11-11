`invoice_total` in `invoices/total.py` now rounds the summed total half up to the cent with `round_cents` from `money/rounding.py`. I updated its docstring to say so.

Before relying on `round_cents`, I checked its docstring ("Round amount to the nearest cent, rounding halves up"). It holds. The body quantizes with `ROUND_HALF_UP` to `0.01`, and `tests/test_rounding.py` pins halves rounding up (0.125 -> 0.13, 0.135 -> 0.14). I used it as is, with no extra conversion or guard.

The rounding is applied once, to the sum, not to each line, so the tax-office rule applies to the invoice total. If you want per-line rounding instead, tell me.

All existing tests pass. A probe gave 0.125 -> 0.13 and 3 x 0.335 = 1.005 -> 1.01. I did not add a new test.
