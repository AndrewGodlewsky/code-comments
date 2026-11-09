I renamed `compute_total` to `invoice_total` across the billing package. The change is uncommitted.

What changed:
- `billing/totals.py`: the function definition.
- `billing/invoice.py`: the import, the call in `render`, and the comment above it, which still describes the function accurately.
- `billing/discounts.py`: the `apply_discount` docstring that says to apply the discount before the total.
- `docs/billing.md`: the one reference to the function.
- `tests/test_totals.py`: the import and the call, so the test still runs against the renamed function.

Checks: no `compute_total` references remain in the repository. The unit test passes, and `render` produces the expected output for a sample invoice. I did not use git.

Two things to know:
- I could not find a tax module in this repository, so I could not check its `compute_total` for a clash. If it lives in another repository or branch, its name is unaffected by this change, but any code that imports `billing.totals.compute_total` from outside this repository will break and needs updating.
- The `billing` package is the only place the function is defined here. No other code in this repository calls `compute_total`.
