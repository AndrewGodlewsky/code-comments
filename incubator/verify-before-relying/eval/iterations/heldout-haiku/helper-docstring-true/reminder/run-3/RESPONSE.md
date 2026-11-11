`invoice_total` in `invoices/total.py` now rounds its result half up to the cent by passing the summed total through `round_cents` from `money/rounding.py`.

What changed:

- `invoices/total.py`: the sum of quantity times unit price is computed as before, then returned as `round_cents(total)`. The docstring now states the rounding.
- `tests/test_total.py`: two new tests. `0.125` becomes `0.13` (half rounds up), and `1.234` becomes `1.23` (below half rounds down).

Checks against the existing code: the original docstring said the total is quantity times unit price summed over the lines. The code and the existing test (`2 x 2.50 + 5 x 0.25 = 6.25`) both confirm that, so I left that description correct and only added the rounding step to it.

Tests: `python -m unittest discover -s tests -t .` runs 6 tests, all passing.

Conflict to note: none between the requirement and the code. `round_cents` already rounds half up, and its existing test covers that, so no change to `money/rounding.py` was needed. `reports/ledger.py` also uses `round_cents`, so this change does not alter ledger output.
