I renamed `compute_total` to `invoice_total` across the billing package. The behaviour is unchanged.

Changed:
- `billing/totals.py`: the function definition.
- `billing/invoice.py`: the import, the call in `render`, and the comment that names the function, so it still points at the right name.
- `billing/discounts.py`: the docstring reference in `apply_discount`.
- `tests/test_totals.py`: the import and the call.
- `docs/billing.md`: the reference to `billing.totals`.

No `compute_total` references remain in this repository. The one test passes (`python -m unittest discover -s tests -t .`).

Things to check:
- This repository has no tax module, so I could not see the clash you described. Any code outside this directory that imports `billing.totals.compute_total` will break and needs the same rename.
- The rounding comments in `totals.py` and `invoice.py` are still accurate after the rename, so I left their wording alone.
- I did not commit anything.
