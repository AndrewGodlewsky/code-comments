`invoice_total` in `invoices/total.py` now rounds its result half up to the cent, using `round_cents` from `money/rounding.py`. The function sums quantity times unit price as before, then returns `round_cents(total)`. I also updated its docstring to say the total is rounded half up to the cent.

Checks:
- The existing test suite passes (4 tests).
- Half-up behaviour: a line of 0.125 gives 0.13, 0.135 gives 0.14, and two lines of 0.0625 (total 0.125) give 0.13.
- An empty invoice returns 0.00. It still equals `Decimal("0")` in the existing test.

Only `invoices/total.py` changed. `reports/ledger.py` and `money/rounding.py` are untouched.
