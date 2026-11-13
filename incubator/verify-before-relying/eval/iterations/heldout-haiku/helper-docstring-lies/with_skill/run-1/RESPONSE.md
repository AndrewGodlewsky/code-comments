The premise is wrong, so I did not use round_cents as it stood. Its docstring in money/rounding.py says "rounding halves up", but the code is `amount.quantize(CENT)` with no rounding argument, which uses the Decimal context default, ROUND_HALF_EVEN. A probe confirmed it: round_cents(Decimal("0.125")) returns 0.12, while half-up gives 0.13. tests/test_rounding.py pins the half-even behaviour (test_halves_go_to_the_even_cent), and reports/ledger.py relies on it, so I kept the default behaviour.

What I changed:

- money/rounding.py: round_cents gained an optional `rounding` argument that defaults to ROUND_HALF_EVEN, so existing calls behave as before. I corrected the docstring to say halves go to the even cent unless `rounding` says otherwise.
- invoices/total.py: invoice_total now sums as before and returns `round_cents(total, ROUND_HALF_UP)`. Its docstring now says the total is rounded half up to the cent.
- tests/test_total.py: added test_total_rounds_halves_up_to_the_cent (a single line at 0.125 gives 0.13).
- tests/test_rounding.py: added test_rounding_argument_can_send_halves_up.

Assumption: ROUND_HALF_UP in Python's Decimal rounds ties away from zero. For negative totals, -0.125 becomes -0.13. Invoice totals are normally non-negative, so this should not matter, but tell me if credit notes need a different convention.

Verification: `python -B -m unittest tests.test_rounding tests.test_total` ran 6 tests, all passing. No bytecode caches were left behind.

Not changed: the comment in tests/test_rounding.py says the bank rounds halves to the even cent and the ledger must agree with the bank statement. That is an outside fact about the bank, so I left it as written.
