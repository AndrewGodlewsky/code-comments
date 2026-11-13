`invoice_total` in `invoices/total.py` now sums quantity times unit price over the lines and rounds the sum half up to the cent with `round_cents`. All 6 tests pass.

- **Helper check:** The `round_cents` docstring says it rounds to the nearest cent, halves up. I checked that against the code, which uses `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`, and against `tests/test_rounding.py`, which has half cases such as 0.125 giving 0.13. They match, so I used the helper as is and found no wrong descriptions to correct.
- **Where rounding happens:** It happens once, on the total, not on each line. I updated the `invoice_total` docstring to say so. If the tax office wants each line rounded before summing, that is a small change, but the totals can differ by a cent.
- **Negative totals:** `ROUND_HALF_UP` rounds halves away from zero, so -0.125 becomes -0.13. This only matters if you issue credit notes through this function.
- **Tests:** I added two tests to `tests/test_total.py`. One covers half-up rounding of the total, and the other checks that the sum is rounded, not each line.
- **Conflicts:** None with any stated requirement.
