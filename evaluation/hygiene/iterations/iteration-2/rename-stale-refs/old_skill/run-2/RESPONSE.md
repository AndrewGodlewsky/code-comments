I renamed `compute_total` to `invoice_total` across the billing package.

Changed:
- `billing/totals.py`: the function definition.
- `billing/invoice.py`: the import, the call, and the comment that mentions it. The comment still describes the behaviour (each line is rounded before summing), so only the name changed.
- `billing/discounts.py`: the docstring reference.
- `docs/billing.md`: the reference to `billing.totals.invoice_total`.
- `tests/test_totals.py`: the import and the call.

No `compute_total` references remain in the repository. The test suite passes (`python -m unittest discover -s tests -t .`, 1 test, OK).

I did not touch the tax module, since it is outside this repository. If it still defines its own `compute_total`, nothing here conflicts with it now. Any caller that imports `billing.totals.compute_total` from outside this repository will break and needs the same rename.
