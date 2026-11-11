The premise is wrong: the `round_cents` docstring in `money/rounding.py` says it rounds halves up, but it does not. It calls `amount.quantize(CENT)` with no rounding mode, so Decimal's default context applies, which is ROUND_HALF_EVEN. `tests/test_rounding.py` pins this (0.125 -> 0.12), and the ledger relies on it because the bank rounds halves to the even cent. So using `round_cents` as it stands would not give the tax office's half-up rounding.

What I did:
- `money/rounding.py`: `round_cents` now takes an optional `rounding` argument. The default is unchanged, so `reports/ledger.py` and the existing rounding tests behave as before. I corrected the docstring to say halves go to the even cent by default.
- `invoices/total.py`: `invoice_total` sums the lines as before, then returns `round_cents(total, ROUND_HALF_UP)`. The docstring notes the tax-office rounding.
- `tests/test_total.py`: added a test that 0.125 gives 0.13 and 0.135 gives 0.14.

Existing tests plus the new one pass. The other claims I checked (the `invoice_total` docstring and the ledger docstring) are accurate and were left as they were.
