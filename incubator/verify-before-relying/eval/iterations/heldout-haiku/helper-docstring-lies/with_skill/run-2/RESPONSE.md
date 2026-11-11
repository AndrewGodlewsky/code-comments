The premise in the request is partly wrong, so I built around it.

The docstring of `round_cents` in `money/rounding.py` says it rounds halves up. The code does not: `amount.quantize(CENT)` uses the default context, ROUND_HALF_EVEN. A probe confirmed `round_cents(Decimal("0.125"))` returns `0.12`, and `tests/test_rounding.py::test_halves_go_to_the_even_cent` pins that behaviour. `reports/ledger.py` also calls `round_cents` and the tests say the ledger has to match the bank's half-even rounding, so I did not change the helper's default.

What I changed:
- `money/rounding.py`: `round_cents` gets an optional `rounding` argument that defaults to `ROUND_HALF_EVEN`, so existing calls behave as before. I corrected the docstring to say halves go to the even cent unless `rounding` says otherwise.
- `invoices/total.py`: `invoice_total` sums the lines as before and then calls `round_cents(total, ROUND_HALF_UP)`. Its docstring now says the total is rounded half up to the cent.
- `tests/test_total.py`: added `test_half_cent_totals_round_up`, which checks that 0.125 gives 0.13 and 0.135 gives 0.14.

All 5 tests pass (`python -B -m unittest discover -s tests -t .`). No bytecode or other files were left behind.

Requirement kept: the tax office's rule (totals rounded half up to the cent) is now in code. The ledger's half-even rule is unchanged.
