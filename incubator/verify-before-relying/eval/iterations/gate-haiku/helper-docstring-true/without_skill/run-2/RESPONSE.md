I changed `invoice_total` in `invoices/total.py` so it rounds the summed total half up to the cent, using `round_cents` from `money/rounding.py`.

The function now imports `round_cents`, sums quantity times unit price as before, and returns `round_cents(total)`. The docstring notes the rounding.

Checks:
- The existing unit tests in `tests/test_total.py` still pass (4 tests across the invoice and rounding suites).
- Spot checks: a total of 0.125 gives 0.13, 0.135 gives 0.14, three lines of 0.10 give 0.30, and an empty invoice gives 0.00.

One behaviour change: an empty invoice now returns `Decimal("0.00")` rather than `Decimal("0")`. These compare equal, so the existing test passes, but any code that relies on the exact representation will see the two-place form.

I did not add a test for the half-up case in `invoice_total` itself. The helper's own tests in `tests/test_rounding.py` already cover halves, so this is a candidate follow-up if you want the invoice-level behaviour pinned down too.
