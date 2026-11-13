I changed `invoice_total` in `invoices/total.py` to round the summed total with `round_cents` from `money/rounding.py`.

- I checked the helper first. `round_cents` quantizes to 0.01 with `ROUND_HALF_UP`, which matches its docstring and the tax office rule.
- Rounding happens once, on the final sum, not per line. If the tax office wants each line rounded before summing, that is a one-line change. Tell me if so.
- I updated the docstring to say the total is rounded half up to the cent.
- A total of 0.125 now returns 0.13. An empty invoice returns 0.00, which still equals Decimal("0"), so the existing tests pass.
- I did not add a test for the new rounding behaviour.
