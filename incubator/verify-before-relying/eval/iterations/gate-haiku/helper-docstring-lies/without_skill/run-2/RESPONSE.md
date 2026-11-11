I changed `invoice_total` in `invoices/total.py` to round the total half up to the cent, but I did not route it through `round_cents`, because that helper does not round half up.

`money/rounding.py` says `round_cents` rounds halves up, but `amount.quantize(CENT)` uses the default rounding mode, ROUND_HALF_EVEN. Checked directly: 0.125 becomes 0.12, 0.135 becomes 0.14, and 2.345 becomes 2.34. Half up would give 0.13, 0.14 and 2.35. `tests/test_rounding.py` asserts the half-even behaviour on purpose (it says the bank rounds halves to the even cent), and `reports/ledger.py` also calls `round_cents`. Changing the helper to half up would break that test and change ledger output, so I left it as it is.

Instead, `invoice_total` sums the lines and then calls `quantize(CENT, rounding=ROUND_HALF_UP)`, with a comment explaining why it does not call `round_cents`. I added `test_total_rounds_halves_up_to_the_cent` to `tests/test_total.py`. All 5 tests pass.

Decision for you: the tax office rule and the bank rule now disagree on halves. If invoice totals should follow the helper's documented intent, the helper's rounding and its test need to be fixed together. That is a separate change, because it would also alter the ledger. Please tell me which rule should apply to the ledger.
