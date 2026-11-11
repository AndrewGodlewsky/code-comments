`invoice_total` now rounds the summed total half up to the cent. All six tests pass (`python -m unittest`).

There was a conflict with the existing helper. `round_cents` in `money/rounding.py` said it rounds halves up, but it actually rounds halves to the even cent (`Decimal.quantize` default). The test `test_halves_go_to_the_even_cent` and the ledger in `reports/ledger.py` depend on that behaviour, because finance reconciles to the bank, which rounds halves to even. So I did not change the default.

What changed:
- `money/rounding.py`: `round_cents(amount, rounding=ROUND_HALF_EVEN)` takes an optional rounding mode. Its docstring now states the real behaviour (halves to the even cent unless told otherwise). The old docstring was wrong.
- `invoices/total.py`: `invoice_total` sums the lines as before, then calls `round_cents(subtotal, rounding=ROUND_HALF_UP)`. Its docstring mentions the rounding.
- Tests: added `test_total_rounds_halves_up_to_the_cent` (0.125 + 0.135 gives 0.26) and `test_rounding_mode_can_send_halves_up` (0.125 gives 0.13).

Ledger behaviour is unchanged. If you actually want half-up everywhere, including the ledger, that would break the bank reconciliation and the even-cent test, so please confirm before I change it.
