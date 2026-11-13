`invoice_total` in `invoices/total.py` now rounds the summed total half up to the cent with `round_cents` from `money/rounding.py`. All 6 tests pass.

- **Helper check:** the `round_cents` docstring ("nearest cent, rounding halves up") matches its code (`quantize` with `ROUND_HALF_UP`) and its tests (0.125 gives 0.13, 0.135 gives 0.14), so I relied on it as written. I found no conflicting comments or docs.
- **Rounding point:** I round once, on the sum of all lines, not on each line. That matches "invoice totals are rounded", but if the tax office wants each line rounded before summing, the results can differ. Tell me if you need per-line rounding.
- **Empty invoice:** it now returns `Decimal("0.00")` instead of `Decimal("0")`. This still compares equal to zero, so the existing test passes.
- **Docstring and tests:** I updated the `invoice_total` docstring to mention the rounding. I added two tests in `tests/test_total.py`, one for half-up rounding (0.125 gives 0.13) and one for the empty invoice at cent precision.
