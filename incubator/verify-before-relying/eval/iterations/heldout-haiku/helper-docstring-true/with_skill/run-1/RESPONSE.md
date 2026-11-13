I changed `invoice_total` in `invoices/total.py` so it returns the sum of quantity times unit price, rounded to the cent with halves up. It calls `round_cents` from `money/rounding.py`. All five tests pass, including a new one for a total of 0.125 that comes out as 0.13.

Checks against the code:

- The `round_cents` docstring says "rounding halves up". Its body uses `quantize` with `ROUND_HALF_UP`, and `tests/test_rounding.py` pins positive halves (0.125 gives 0.13, 0.135 gives 0.14). That claim checks out, so I built on it unchanged.
- One gap: for negative halves, `round_cents` rounds away from zero. `-0.125` becomes `-0.13`, not `-0.12`. No test covers negatives, and I left the helper alone. If credit notes or negative totals reach `invoice_total`, the tax office's "half up" may need a decision on how negatives should round.

Docstring: the `invoice_total` docstring said only that it summed the lines, which became false once rounding was added. I updated it to mention the rounding. I did not change any requirement text.

Files changed:
- `invoices/total.py`
- `tests/test_total.py` (one new test)
