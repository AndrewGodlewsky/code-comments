`invoice_total` now rounds its result to the cent, halves up, as the tax office requires.

The `round_cents` helper did not do what its docstring says. It said "rounding halves up", but it called `quantize(CENT)` with no rounding mode, so it uses Python's default, round-half-even. `tests/test_rounding.py` pins that behaviour on purpose, because the ledger has to match the bank to the cent. So I could not use it unchanged for half-up.

What I changed:

- `money/rounding.py`: `round_cents(amount, rounding=ROUND_HALF_EVEN)` takes an optional rounding mode. The default is still half-even, so the ledger and its test behave exactly as before. The docstring now states the real default.
- `invoices/total.py`: `invoice_total` sums the lines as before, then returns `round_cents(total, rounding=ROUND_HALF_UP)`.

Checks: all 4 unit tests pass. Totals of 0.125 give 0.13 and 2.675 give 2.68. Three lines of quantity 3 at 0.045 (total 0.135) give 0.14. `round_cents(Decimal("0.125"))` still gives 0.12 for the ledger.

Decision for you: if the bank and the tax office should both use half-up, the ledger's rounding would also need to change. That would mean changing `test_halves_go_to_the_even_cent` and reconciling with the bank, so I left it alone.
