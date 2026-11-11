`invoice_total` now rounds half up to the cent, using `round_cents`.

What changed:
- `money/rounding.py`: `round_cents` takes an optional `rounding` argument, defaulting to `ROUND_HALF_EVEN`. Its old docstring said it rounded halves up, but it actually rounded half to even. I corrected the docstring. Default behaviour is unchanged, so `reports/ledger.py` and the existing rounding test behave as before.
- `invoices/total.py`: `invoice_total` sums the lines, then calls `round_cents(total, rounding=ROUND_HALF_UP)`.
- Tests: added a half-up case for `invoice_total` (0.125 + 0.010 gives 0.14) and a test that the rounding mode can be chosen. All 6 tests pass.

Please check one thing: the ledger rounds half to even on purpose, because the test notes say the bank does too. I left the ledger on that default. If the tax office rule should also apply to the ledger, tell me and I will change it, but that would break agreement with the bank statement.
