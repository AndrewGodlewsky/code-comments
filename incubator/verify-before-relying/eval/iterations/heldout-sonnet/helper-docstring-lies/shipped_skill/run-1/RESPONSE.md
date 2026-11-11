`invoice_total` now rounds half up to the cent, but it does not use `round_cents`, because that helper can't do half up.

`round_cents` in `money/rounding.py` rounds halves to the even cent. Its docstring said "halves up", which was wrong. `tests/test_rounding.py` expects 0.125 to give 0.12, and it records that the bank rounds halves to even. `reports/ledger.py` relies on that so the ledger matches the bank statement. Changing the helper would break the ledger, so I left its behaviour alone.

What I changed:
- `invoices/total.py`: the total is quantized to `CENT` (imported from `money.rounding`) with `ROUND_HALF_UP`. A short comment explains why it doesn't call `round_cents`, and the docstring now states the rounding.
- `money/rounding.py`: corrected the `round_cents` docstring to say halves go to the even cent. No code change there.
- `tests/test_total.py`: added a test that 0.125 gives 0.13 and 0.135 gives 0.14.

The tests pass. If you'd rather have a shared half-up helper in `money/`, say so and I'll add one.
