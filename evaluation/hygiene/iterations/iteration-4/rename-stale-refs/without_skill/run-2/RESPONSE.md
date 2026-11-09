I renamed `compute_total` to `invoice_total` across the billing package. No references to `compute_total` remain in the repository, and the unit test passes.

Changes:
- `billing/totals.py`: the function definition is now `invoice_total`.
- `billing/invoice.py`: the import, the call, and the comment now use `invoice_total`.
- `billing/discounts.py`: the docstring reference now uses `invoice_total`.
- `docs/billing.md`: the reference now reads `billing.totals.invoice_total`.
- `tests/test_totals.py`: the import and the call now use `invoice_total`.

The rename is a plain find-and-replace on whole-word matches, so the behaviour is unchanged. `python -m unittest discover -s tests` reports OK.

Things to check:
- The new tax module is not in this repository, so I could not confirm that its `compute_total` is gone or that the two names no longer clash. Code that imports `billing.totals.compute_total` from outside this repo will now fail with an ImportError. I did not add a backwards-compatible alias, because you asked for a rename.
