I changed `invoice_total` in `invoices/total.py` so it now returns the summed total passed through `round_cents` from `money/rounding.py`. That rounds half up to the cent, as the tax office requires. Rounding is applied once to the invoice total, not to each line.

Changes:
- `invoices/total.py`: imports `round_cents`, sums the lines into `total`, and returns `round_cents(total)`. A comment beside the call records the tax office requirement and why rounding happens on the total. The docstring now says the result is rounded half up to the cent.
- `tests/test_total.py`: added `test_total_rounds_half_up_to_the_cent`, which checks that a single line of 0.125 gives 0.13.

The unit tests pass (5 tests, OK).

Decision for you: the tax office rule says "invoice totals", and I read that as rounding the summed total rather than each line. If the tax office expects per-line rounding, tell me and I will change it.

Nothing else in the repository was changed. `reports/ledger.py` already rounds its own amounts and does not call `invoice_total`.
