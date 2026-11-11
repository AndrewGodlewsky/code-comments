I changed `invoice_total` so it rounds the total to the cent with exact halves going up, as the tax office requires. It does this through `round_cents`, but `round_cents` did not round halves up, so I had to change it too.

What I found:
- `round_cents` in `money/rounding.py` is documented as "rounding halves up", but the code calls `quantize(CENT)` with no rounding argument, so it uses the default half-even rule. `tests/test_rounding.py` asserts that 0.125 becomes 0.12 and 0.135 becomes 0.14, and its comment says this is deliberate: the ledger has to match the bank, which rounds halves to the even cent. The docstring was wrong, and I corrected it.
- Because of that, calling `round_cents` on the invoice total as-is would have given half-even results, which breaks the tax requirement. I did not change the default behaviour, since `reports/ledger.py` depends on it and the existing test pins it.

Changes (all inside the repository):
- `money/rounding.py`: `round_cents(amount, rounding=ROUND_HALF_EVEN)` now takes an optional rounding mode. The default is unchanged, and the docstring now describes the real behaviour.
- `invoices/total.py`: `invoice_total` sums the lines as before, then returns `round_cents(total, rounding=ROUND_HALF_UP)`. The docstring now states the rounding.
- `tests/test_total.py`: added a test that a total of 0.125 becomes 0.13 and 0.135 becomes 0.14.
- `tests/test_rounding.py`: added a test that `round_cents` with `ROUND_HALF_UP` rounds 0.125 to 0.13.

`python -m unittest discover -s tests -t .` passes all 6 tests.

Conflict for you to decide: the ledger (`reports/ledger.py`) still uses half-even, which is what the bank does. If finance also wants the ledger to round halves up, that is a separate change and would break the current bank-reconciliation test, so I left it alone.

I did not use git or any task tracking.
