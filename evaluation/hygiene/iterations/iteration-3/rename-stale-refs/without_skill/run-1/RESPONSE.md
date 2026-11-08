I renamed `compute_total` to `invoice_total` throughout the billing package. The rename is complete and the test suite passes (1 test, OK).

What changed:
- `billing/totals.py`: the function definition is now `invoice_total`.
- `billing/invoice.py`: the import and the call site, plus the comment that names the function.
- `billing/discounts.py`: the docstring that refers to the function.
- `tests/test_totals.py`: the import and the call in the test.
- `docs/billing.md`: the reference to `billing.totals.compute_total`. I changed it too, because it would otherwise point at a name that no longer exists.

No `compute_total` references remain in the repository.

Things to check:
- This repository has no tax module. I could not see the `compute_total` in the new tax module, so I could not confirm the two names no longer clash. The tax module's function is untouched, since I only edited files in this repository.
- Any code outside this repository that imports `billing.totals.compute_total` will break. I did not search for callers outside this directory.
- I did not commit anything.
