`invoice_total` in `invoices/total.py` now rounds the total half up to the cent by passing it through `round_cents` from `money/rounding.py`.

- I checked the helper before relying on it. It quantizes with `ROUND_HALF_UP`, and the existing rounding tests cover halves (0.125 -> 0.13).
- Rounding happens once, on the summed total, not per line. If the tax office wants each line rounded before summing, that is a different result in some cases. Tell me and I'll change it.
- The result now always has two decimal places, so an empty invoice returns `Decimal("0.00")`. That still compares equal to `Decimal("0")`.
- I added a test for half-up rounding of the total. All 5 tests pass.
