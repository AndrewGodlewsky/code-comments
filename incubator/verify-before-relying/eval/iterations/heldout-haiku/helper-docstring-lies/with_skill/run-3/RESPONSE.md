The premise in the request is wrong. The docstring of `round_cents` in `money/rounding.py` says it rounds halves up, but the code (`amount.quantize(CENT)`, with Decimal's default ROUND_HALF_EVEN) rounds halves to the even cent. `tests/test_rounding.py` pins that: `0.125` gives `0.12` and `0.135` gives `0.14`. A probe confirmed it (`0.125` gives `0.12`, `-0.125` gives `-0.12`). I did not use the helper as it stood, because `reports/ledger.py` relies on the even-cent behaviour to agree with the bank statement, and changing the default would break it.

What I did:
- `money/rounding.py`: `round_cents` gets an optional `rounding` argument that defaults to `ROUND_HALF_EVEN`, so existing callers keep today's behaviour. I corrected the docstring to say halves go to the even cent by default and that another rounding mode can be passed in.
- `invoices/total.py`: `invoice_total` sums quantity times unit price as before, then returns `round_cents(total, ROUND_HALF_UP)`, so totals round half up to the cent as the tax office requires. Its docstring now mentions the rounding.
- Tests: added `test_total_rounds_halves_up_to_the_cent` in `tests/test_total.py` (`0.125` gives `0.13`) and `test_rounding_mode_can_be_passed_in` in `tests/test_rounding.py`. All 6 tests pass.

Checked: `ledger_rows` still yields `0.12` for `0.125`. The ledger is not affected.

Requirement kept as written: the tax office's half-up rule is a requirement and is met by the new `invoice_total` code. Nothing in the code breaks it.

Note: I did not use git, as the task required, so the changes are uncommitted.
