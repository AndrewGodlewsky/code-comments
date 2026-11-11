I changed `invoice_total` in `invoices/total.py` so the invoice total is rounded half up to the cent. It now sums quantity times unit price as before, then passes the result through `round_cents` from `money/rounding.py`. The docstring now says the total is rounded half up to the cent.

I added a test, `test_total_is_rounded_half_up_to_the_cent` in `tests/test_total.py`, which checks that a total of 0.135 becomes 0.14. The full suite passes (5 tests) with `python -m unittest discover -s tests -t .`.

Nothing else changed. The ledger in `reports/ledger.py` already uses `round_cents`, so it is unaffected.
