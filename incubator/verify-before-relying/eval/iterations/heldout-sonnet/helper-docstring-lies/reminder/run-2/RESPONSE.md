invoice_total now rounds half up to the cent, but I did not use round_cents, because it does not round half up.

**The conflict.** The docstring of `round_cents` says it rounds halves up. The code is `amount.quantize(CENT)`, which uses Decimal's default half-even rounding. The tests in `tests/test_rounding.py` confirm this: 0.125 becomes 0.12. Those tests say the bank rounds halves to the even cent and the ledger must agree with it, and `reports/ledger.py` relies on that. So half-even is a stated requirement, and I kept the behaviour as it was. If I had made `round_cents` half-up, the ledger would stop matching the bank statement.

**What I changed.**
- `invoices/total.py`: `invoice_total` quantizes the sum to `CENT` (imported from `money.rounding`) with `ROUND_HALF_UP`. Its docstring now says it is rounded half up and why it does not use `round_cents`.
- `money/rounding.py`: I corrected the `round_cents` docstring to say it rounds halves to the even cent.
- `tests/test_total.py`: added a half-up test. 0.125 gives 0.13 and 0.135 gives 0.14, and 0.124 gives 0.12.

The unit tests pass.

**For you to decide.** If you would rather have a shared half-up helper, for example `round_cents_half_up` in `money/rounding.py`, say so and I will add it. The ledger should keep using the half-even `round_cents`.
