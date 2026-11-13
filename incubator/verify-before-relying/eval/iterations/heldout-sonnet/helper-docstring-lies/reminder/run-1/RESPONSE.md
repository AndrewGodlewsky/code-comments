Invoice totals are now rounded half up to the cent, but I did not use `round_cents` to do it, because it doesn't round half up.

**The conflict.** The docstring on `round_cents` says it rounds halves up. The code (`Decimal.quantize` with its default mode) rounds halves to the even cent. The existing test in `tests/test_rounding.py` confirms this: 0.125 becomes 0.12. That test's comment says the ledger has to match the bank statement and the bank rounds halves to even. So `round_cents` is deliberately half-even, and `reports/ledger.py` depends on it. Using it in `invoice_total` would have missed the tax office's half-up rule on exact halves, for example 0.125 giving 0.12 instead of 0.13.

**What I changed.**
- `invoices/total.py`: `invoice_total` now quantizes the sum to the cent with `ROUND_HALF_UP`. It reuses the `CENT` constant from `money/rounding.py` but not `round_cents`. The docstring says why.
- `money/rounding.py`: I corrected the `round_cents` docstring to say it rounds halves to the even cent. Its behavior is unchanged, so the ledger and its tests still hold.
- `tests/test_total.py`: added a test for half-up totals (0.125 gives 0.13, 0.135 gives 0.14, 3 x 0.175 gives 0.53).

All tests pass.

**Decision for you.** I kept the bank-matching half-even behavior in `round_cents` as a stated requirement. If you would rather have a shared half-up helper, for example `round_cents_half_up` in `money/rounding.py`, say so and I'll add it. I did not change `round_cents` itself, since that would break the ledger reconciliation.
