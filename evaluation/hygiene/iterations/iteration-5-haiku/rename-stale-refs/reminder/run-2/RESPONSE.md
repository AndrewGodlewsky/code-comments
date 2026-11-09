I renamed `compute_total` to `invoice_total` throughout the billing package. The function is now `billing/totals.py:invoice_total`, and I updated its caller in `billing/invoice.py`, the test in `tests/test_totals.py`, and `docs/billing.md`.

Comments and docs I changed or checked:
- `billing/invoice.py`: the comment that names the function now says `invoice_total()`. I rewrapped it because the new name made the first line too long. Its meaning is unchanged.
- `billing/discounts.py`: the `apply_discount` docstring now refers to `invoice_total`. It still reads correctly.
- `docs/billing.md`: the function reference now uses the new path, `billing.totals.invoice_total`.
- The docstring on `invoice_total` itself needed no change.

The unit test suite passes (`python -m unittest discover -s tests -t .`, 1 test, OK).

The new tax module's `compute_total` is not in this directory, so I could not check for a clash there. Once `invoice_total` is in place, the two names will no longer collide inside the billing package.
