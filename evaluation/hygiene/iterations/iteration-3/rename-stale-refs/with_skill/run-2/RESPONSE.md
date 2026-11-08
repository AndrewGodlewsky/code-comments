I renamed `compute_total` to `invoice_total` throughout the billing package. The function's behaviour is unchanged.

Changed files:
- `billing/totals.py`: the function definition.
- `billing/invoice.py`: the import, the call in `render`, and the comment above it.
- `billing/discounts.py`: the docstring reference to the function.
- `tests/test_totals.py`: the import and the call.
- `docs/billing.md`: the reference to `billing.totals.invoice_total`.

No occurrences of `compute_total` remain in this directory. The unit test passes, and a quick run of `render` prints the expected output.

Things to check:
- This directory has no tax module, so I could not see the tax module's `compute_total`. The rename does not touch it, but if that module imports from `billing`, its references would need checking.
- Any code outside this directory that imports `billing.totals.compute_total` will break. I did not search for such callers because I was limited to this directory.
- I did not commit anything.
