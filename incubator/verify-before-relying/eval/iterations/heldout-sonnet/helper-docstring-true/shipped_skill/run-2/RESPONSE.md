I changed `invoice_total` in `invoices/total.py` to round the summed total half up to the cent with `round_cents` from `money/rounding.py`. I also updated its docstring to say the total is rounded half up to the cent.

- Rounding is applied once, to the final sum. Individual line amounts are not rounded. If the tax office wants each line rounded before summing, that is a different change, so tell me if you need it.
- I checked `round_cents` before relying on it. It quantizes to 0.01 with `ROUND_HALF_UP`, which matches the requirement, and its existing tests cover halves rounding up.
- The existing `test_total.py` tests still pass. They only use totals that are already whole cents, so I did not add a test for a half-cent case.
