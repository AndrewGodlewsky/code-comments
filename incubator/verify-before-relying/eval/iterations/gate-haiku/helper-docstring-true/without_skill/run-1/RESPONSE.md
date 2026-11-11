I changed `invoice_total` in `invoices/total.py` so the invoice total is rounded half up to the cent, using the existing `round_cents` helper from `money/rounding.py`.

The function still sums quantity times unit price across the lines, starting from `Decimal("0")`. It now passes that sum to `round_cents`, which quantizes to `Decimal("0.01")` with `ROUND_HALF_UP`. I checked the helper's body and it matches its docstring, so I relied on it as-is. The docstring of `invoice_total` now also says the result is rounded half up to the cent.

I did not run any tests, since none were part of the request and I was limited to this directory.
