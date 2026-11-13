I added an optional `currency` argument to `round_price` in `pricing/rounding.py`.

- `round_price(amount, "CHF")` rounds to the nearest 0.05 CHF, halves rounding up. The result keeps two decimal places, so 2.07 becomes 2.05 and 2.08 becomes 2.10.
- `round_price(amount)`, or any currency other than "CHF", takes the same path as before and rounds to the cent.

The docstring now describes both behaviours, and the 0.05 step is a named constant, `CHF_CASH_STEP`, with a comment giving the reason (Swiss cash prices).

I added three CHF tests and one check that the no-currency and EUR paths still round to the cent. All 8 tests pass.

Points to note:
- No caller passes a currency yet. `add_vat`, `line_total`, `daily_total` and `price_label` all keep their current cent rounding. If CHF cash rounding should also apply to invoice totals or shop labels, those callers need to pass "CHF" and I can change them.
- Any currency code other than "CHF" is treated as cent rounding, with no error raised for unknown codes.
- I did not record an issue or ticket id for the CHF rule, because none was given. If one exists, it should be added to the `CHF_CASH_STEP` comment.
