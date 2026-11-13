invoice_total now rounds the total half up to the cent, as the tax office requires.

What changed:
- invoices/total.py: invoice_total sums the lines as before, then calls round_cents with ROUND_HALF_UP. A comment records the tax office requirement.
- money/rounding.py: round_cents takes an optional rounding argument and still defaults to half-even. Its old docstring said it rounded halves up, which was false: it used Decimal's default, half-even. The docstring now states the real default.
- tests/test_total.py: new test that a 0.125 total becomes 0.13.
- tests/test_rounding.py: new test that round_cents accepts ROUND_HALF_UP.

Why round_cents keeps half-even by default: reports/ledger.py uses it, and tests/test_rounding.py says the ledger must match the bank statement, which rounds halves to the even cent. Switching the default to half-up would have changed the ledger's amounts, so I added the option instead.

Tests: all 6 unit tests pass (python -m unittest discover -s tests -t .).

Not done: I did not commit, and I did not use git or any tracker. The tests/test_rounding.py comment states the bank rule, and I left it unchanged.
