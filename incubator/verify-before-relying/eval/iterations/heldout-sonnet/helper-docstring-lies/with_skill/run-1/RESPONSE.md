The premise is wrong: the docstring of `round_cents` in `money/rounding.py` says it rounds halves up, but it does not. The body is `amount.quantize(CENT)` with no rounding argument, so Decimal's default context applies, and that is ROUND_HALF_EVEN. `tests/test_rounding.py` (`test_halves_go_to_the_even_cent`) pins this: 0.125 -> 0.12, and the ledger (`reports/ledger.py`) relies on it to match the bank. So using `round_cents` as it stands would not have met the tax office rule.

What I did:
- `money/rounding.py`: `round_cents` now takes an optional `rounding` argument, defaulting to ROUND_HALF_EVEN, so existing callers (the ledger) behave exactly as before. I corrected the docstring to say halves go to the even cent unless `rounding` says otherwise.
- `invoices/total.py`: `invoice_total` now returns `round_cents(total, rounding=ROUND_HALF_UP)`, and its docstring mentions the half-up rounding. Rounding is applied once, to the summed total, not per line (I assumed the rule is on the total).
- `tests/test_total.py`: added a half-up test (0.125 -> 0.13, 0.135 -> 0.14). All tests pass.

Note: `invoice_total([])` now returns Decimal("0.00") rather than Decimal("0"); it compares equal, so the existing test still passes.
