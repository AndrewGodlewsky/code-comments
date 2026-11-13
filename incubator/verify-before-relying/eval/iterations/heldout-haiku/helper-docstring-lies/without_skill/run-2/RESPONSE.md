`invoice_total` now rounds the summed total half up to the cent, as the tax office requires.

`round_cents` could not be used as-is for this. Its docstring says it rounds halves up, but the code calls `Decimal.quantize` with the default rounding mode, which is half-even. `tests/test_rounding.py` pins that behaviour on purpose, because the ledger has to match the bank statement and the bank rounds halves to the even cent. Changing the default would have broken the ledger and that test.

What changed:
- `money/rounding.py`: `round_cents(amount, rounding=ROUND_HALF_EVEN)` takes an optional rounding mode. The default is unchanged, so `reports/ledger.py` behaves exactly as before. The docstring now says the default is half-even; it previously claimed half-up.
- `invoices/total.py`: `invoice_total` sums as before, then returns `round_cents(total, ROUND_HALF_UP)`.
- `tests/test_total.py`: two cases for half-cent totals (0.125 gives 0.13, 0.135 gives 0.14).
- `tests/test_rounding.py`: a case showing `ROUND_HALF_UP` works when passed explicitly.

All 7 tests pass (`python -m unittest discover -s tests -t .`).

Worth knowing: `invoice_total` now rounds, so any caller that needs unrounded sums will need a separate path. I did not check other callers outside this repository.
