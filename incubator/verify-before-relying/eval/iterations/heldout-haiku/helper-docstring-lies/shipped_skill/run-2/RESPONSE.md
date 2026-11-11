I changed `invoice_total` in `invoices/total.py` to round the total half up to the cent, but it does not call `round_cents`. `round_cents` rounds halves to the even cent, not up as its docstring claimed. Its test (`test_halves_go_to_the_even_cent`) and the monthly ledger in `reports/ledger.py` depend on that behaviour to match the bank, so I left it unchanged.

What changed:
- `invoices/total.py`: the total is now quantized to `CENT` with `ROUND_HALF_UP`. A comment there records why `round_cents` is not used.
- `money/rounding.py`: the docstring of `round_cents` now says it rounds halves to the even cent, which is what the code does.
- `tests/test_total.py`: added `test_rounds_halves_up_to_the_cent`, which checks that a line totalling 0.125 gives 0.13.

All 5 tests pass (`python -I -m unittest discover -s tests -t .`).

Decision for you: if the tax office rule should apply to every caller, or the ledger should also move to half up, that would mean changing `round_cents` and its test. That is a separate decision because it would change the ledger's reconciliation with the bank, so I did not make it.
