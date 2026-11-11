`invoice_total` now rounds its total half up to the cent, so 0.125 becomes 0.13 and 4.005
becomes 4.01.

I did not use `round_cents` for this, because it does not round halves up, whatever its
docstring said. It calls `quantize` without a rounding mode, so it gets the decimal module's
default, ROUND_HALF_EVEN: 0.125 becomes 0.12. `tests/test_rounding.py` pins that, because the
ledger has to agree with the bank statement, so I left `round_cents` as it is and corrected
its docstring to say halves go to the even cent. `invoice_total` quantizes with
ROUND_HALF_UP itself. The tests pass.
