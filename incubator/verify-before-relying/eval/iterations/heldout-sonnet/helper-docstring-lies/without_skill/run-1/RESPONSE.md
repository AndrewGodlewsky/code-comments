I changed `invoice_total` to round half up to the cent, but I did not use `round_cents`, because it doesn't round half up.

`round_cents` in `money/rounding.py` has a docstring saying "rounding halves up". The code is a plain `amount.quantize(CENT)`, which uses Decimal's default ROUND_HALF_EVEN. `round_cents(Decimal("0.125"))` returns `0.12`. `tests/test_rounding.py` expects this, and its comment says the ledger has to match the bank statement, which rounds halves to even. `reports/ledger.py` relies on it. If I had changed `round_cents` to half up, the ledger would stop matching the bank. If I had used it as is, invoices would still round half-even and miss the tax office rule.

What I did:
- `invoices/total.py`: the total is now `quantize(CENT, rounding=ROUND_HALF_UP)`. It reuses the `CENT` constant from `money.rounding`. A comment explains why `round_cents` isn't called.
- `tests/test_total.py`: added a test for half-cent totals (0.125 gives 0.13, 0.135 gives 0.14). All tests pass.
- I rounded only the final sum. The request says "invoice totals", so I left line amounts unrounded. Tell me if the tax rule applies per line.

I left `round_cents` and its misleading docstring alone. The docstring should be corrected to say half-even. Or you could add a separate half-up helper if more code will need it. Both are your call.
