I changed `invoice_total` in `invoices/total.py` to round the total half up to the cent, but I did not route it through `round_cents`. That helper rounds halves to even, not half up, so using it would have given the wrong answer for the tax office.

What I found:
- `round_cents` in `money/rounding.py` calls `Decimal.quantize(CENT)` with no rounding argument, so it uses the default ROUND_HALF_EVEN. `round_cents(Decimal("0.125"))` returns 0.12 and `round_cents(Decimal("0.135"))` returns 0.14.
- Its docstring says "rounding halves up", which is wrong. The existing test `test_halves_go_to_the_even_cent` documents the actual behaviour, and the comment there says the ledger must match the bank, which rounds halves to even.
- `reports/ledger.py` depends on `round_cents`, so changing the helper to half up would change the ledger's output and break the bank reconciliation. I left `money/rounding.py` untouched.

What I changed:
- `invoices/total.py`: `invoice_total` sums quantity times unit price as before, then calls `quantize(CENT, rounding=ROUND_HALF_UP)`. It reuses the `CENT` constant from `money/rounding.py`. The docstring explains why `round_cents` is not used.
- `tests/test_total.py`: added `test_total_rounds_halves_up_to_the_cent`, which checks 0.125 gives 0.13 and 0.135 gives 0.14.

Test result: all 5 tests pass (`python -m unittest discover -s tests -t .`).

Decision for you: the docstring on `round_cents` should be corrected to say half to even, or the helper should be changed to half up. Changing the helper is a separate decision, because it would alter the ledger and no longer match the bank statement. I have not made that change.
