`invoice_total` in `invoices/total.py` now rounds the summed total half up to the cent. It does this by calling `round_cents` from `money/rounding.py`.

I read `round_cents` before relying on it. It quantizes to 0.01 with `ROUND_HALF_UP`, which matches its docstring and the existing rounding tests.

- Rounding is applied once, to the final sum, not to each line. If the tax office wants each line rounded before summing, that is a small change. Tell me if so.
- I added a test in `tests/test_total.py` covering halves (0.125 gives 0.13, and 3 x 0.335 = 1.005 gives 1.01).
- The unit tests pass.
