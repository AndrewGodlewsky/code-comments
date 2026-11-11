Invoice totals are now rounded half up to the cent.

What changed, in invoices/total.py:
- `invoice_total` sums quantity times unit price as before, then passes the sum through `round_cents` from money/rounding.py.
- Its docstring now says the total is rounded half up to the cent, so it matches the code.

Checks:
- I read the `round_cents` docstring and body and the tests that pin it. The body uses `ROUND_HALF_UP` and `test_halves_round_up` expects 0.125 to become 0.13, so the claim holds and I built on it as written.
- The existing tests (4 of 4) pass.
- Probes: a total of 0.125 gives 0.13, 1.245 gives 1.25, 0.124 gives 0.12.

One side effect: an empty invoice now returns Decimal("0.00") instead of Decimal("0"). They compare equal, so the existing empty-invoice test still passes.

I did not change any tests or the rounding helper.
