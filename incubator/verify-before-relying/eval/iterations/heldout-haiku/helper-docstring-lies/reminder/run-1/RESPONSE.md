invoice_total now rounds half up to the cent, as the tax office requires. All 7 unit tests pass.

What changed:
- invoices/total.py: invoice_total sums quantity times unit price as before, then calls round_cents(total, rounding=ROUND_HALF_UP). Rounding applies to the invoice total, not to each line.
- money/rounding.py: round_cents takes an optional rounding argument. The default stays ROUND_HALF_EVEN, so the ledger (reports/ledger.py) and its bank reconciliation behave exactly as before.
- tests/test_total.py: added tests for half-up at the cent (0.125 gives 0.13, 0.135 gives 0.14) and for rounding the sum rather than each line.
- tests/test_rounding.py: added a test for the new rounding argument.

Conflict you should know about:
- The round_cents docstring said it rounds halves up, but the code used Decimal.quantize with the default mode, which is half-even. The existing test test_halves_go_to_the_even_cent also pins half-even behaviour (0.125 gives 0.12), and its comment says the bank rounds halves to the even cent. I corrected the docstring to describe the actual behaviour. I did not change the default, because that would break the ledger's bank reconciliation.
- Your requirement (invoice totals round half up) is kept as written. It is implemented by passing ROUND_HALF_UP explicitly from invoice_total.
- Please confirm with finance that the ledger should stay half-even. The tax rule only covers invoices, and I have not changed the ledger.
