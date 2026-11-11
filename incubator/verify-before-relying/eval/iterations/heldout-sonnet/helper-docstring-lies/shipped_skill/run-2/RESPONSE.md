I changed `invoice_total` in `invoices/total.py` to round half up to the cent, but it does not call `round_cents`, because that helper does not round half up.

`round_cents` calls `quantize` with no rounding mode, so it uses the default half-even rounding (0.125 becomes 0.12). Its docstring said "rounding halves up", which was wrong. `tests/test_rounding.py` confirms half-even is intended, because the ledger has to match the bank's rounding. `reports/ledger.py` relies on this, so I left the helper's behavior alone.

What I did:
- `invoice_total` now sums the lines and quantizes the result to `CENT` (imported from `money/rounding.py`) with `ROUND_HALF_UP`. A short comment explains why it does not use `round_cents`.
- I corrected the `round_cents` docstring to say it rounds halves to the even cent.
- I added a half-up test to `tests/test_total.py`. The full test suite passes.

Decision for you: if you want one shared half-up helper, say so and I will add a separate one (for example `round_cents_half_up`) in `money/rounding.py`. Changing `round_cents` itself would change the ledger.
