`invoice_total` in `invoices/total.py` now rounds the summed total half up to the cent using `round_cents` from `money/rounding.py`. I updated its docstring to say so.

I checked the `round_cents` docstring ("nearest cent, rounding halves up") against its body (`quantize` with `ROUND_HALF_UP`) and its tests, and it is accurate, so I used it as it stands.

Rounding is applied once to the final sum, not per line. If the tax office wants each line rounded first, say so and I will change it.

Existing tests pass.
