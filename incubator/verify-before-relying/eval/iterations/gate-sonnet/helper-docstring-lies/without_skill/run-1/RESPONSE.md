`invoice_total` now rounds the total half up to the cent, but it does not use `round_cents`, because `round_cents` doesn't round half up.

`round_cents` in `money/rounding.py` calls `quantize` with the default mode, which is half-even. 0.125 becomes 0.12. Its docstring said "halves up", which was wrong. The existing test `test_halves_go_to_the_even_cent` shows half-even is intended, because the ledger has to match the bank statement. `reports/ledger.py` also uses it. If I had changed the helper, the ledger would have changed too, so I left its behaviour alone.

What I changed:
- `invoices/total.py`: the summed total is rounded with `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`.
- `money/rounding.py`: I corrected the `round_cents` docstring to say it rounds halves to the even cent. This is a comment-only change.
- `tests/test_total.py`: I added a test that 0.125 gives 0.13 and 0.135 gives 0.14.

The tests pass.

Decision for you: I rounded only the final total. If the tax office wants each line rounded before summing, that gives different results and needs a different change. Tell me if so.
