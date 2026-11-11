I changed `invoice_total` in `invoices/total.py` to round the total half up to the cent, but I did not use `round_cents`, and you should know why.

`round_cents` in `money/rounding.py` says in its docstring that it rounds halves up. It doesn't. It calls `quantize(CENT)` with the default rounding mode, which is half-even: `round_cents(Decimal("0.125"))` returns `0.12`. That is intentional for the ledger. `tests/test_rounding.py` says the bank rounds halves to the even cent, and `reports/ledger.py` depends on it. Using the helper would have produced totals the tax office doesn't accept.

What I did:
- `invoice_total` now does `total.quantize(CENT, rounding=ROUND_HALF_UP)`, reusing the `CENT` constant from `money/rounding.py`.
- I added a test in `tests/test_total.py` for half cases (0.125 -> 0.13, 0.135 -> 0.14, 2.675 -> 2.68). The full suite passes.
- I did not touch `round_cents`, since changing it would break the ledger reconciliation.

Decision for you: the `round_cents` docstring is wrong and will mislead the next person. I'd suggest correcting it to say "halves round to even", or adding a separate half-up helper that both places can share. I left it alone because it is outside what you asked for.

Also, I round only the final total, not each line. If the tax office wants each line rounded before summing, tell me and I'll change it.
