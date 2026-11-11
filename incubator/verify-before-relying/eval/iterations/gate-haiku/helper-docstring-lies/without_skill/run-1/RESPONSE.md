I changed `invoice_total` in `invoices/total.py` so it rounds the summed total half up to the cent. I did not call `round_cents`, because it does not round halves up.

`round_cents` is documented as "rounding halves up", but it calls `Decimal.quantize(CENT)` with no rounding argument. That uses the decimal context default, ROUND_HALF_EVEN, so `round_cents(Decimal("0.125"))` returns `0.12`. `tests/test_rounding.py` asserts this half-even behaviour on purpose, because the ledger has to match the bank to the cent. `reports/ledger.py` also depends on it, so I did not change `round_cents`.

The new `invoice_total` sums the lines as before, then applies `quantize(CENT, rounding=ROUND_HALF_UP)`. It reuses the `CENT` constant from `money/rounding.py`. I added `test_total_rounds_halves_up_to_the_cent` to `tests/test_total.py`, using a single line priced at 0.125, which expects 0.13. All 5 tests pass.

Decision for you: `round_cents` and its docstring are wrong, and anything else that needs half-up rounding will hit the same trap. Either give `round_cents` an explicit rounding mode, or keep the half-even ledger behaviour and fix its docstring. Both options touch the ledger, so I left them for you to decide.
