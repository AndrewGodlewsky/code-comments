I renamed `compute_total` to `invoice_total` across the billing package. The unit test passes, and rendering an invoice still gives the right total.

Changed files:
- `billing/totals.py`: the function definition.
- `billing/invoice.py`: the import and call in `render`, plus the comment above it, which I rewrapped to stay under 80 columns.
- `billing/discounts.py`: the docstring reference.
- `docs/billing.md`: the function name in the description.
- `tests/test_totals.py`: the import and call.

No `compute_total` references remain in this directory. I did not add an alias, so any code outside this directory that imports `billing.totals.compute_total` will now fail until it is updated.

I did not find the new tax module in this directory, so I could not check its `compute_total` or any clash with it. If the tax module imports from `billing`, check its imports after this change.
