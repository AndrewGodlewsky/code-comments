I renamed `compute_total` to `invoice_total` across the billing package. The changes are in these files:

- `billing/totals.py`: the function definition.
- `billing/invoice.py`: the import, the call, and the comment above it that names the function.
- `billing/discounts.py`: the `apply_discount` docstring that says to apply it before the total.
- `docs/billing.md`: the function reference.
- `tests/test_totals.py`: the import and the test call.

No references to `compute_total` remain in the repository. The unit test suite passes (1 test, OK).

Two things to check:

1. This repository has no tax module, so I could not see the tax module's `compute_total` and left it alone. If the tax module imports from `billing`, or its docs point at `billing.totals`, those references will need updating too.
2. The rename makes `tests/test_totals.py` line 9 about 87 characters long. I did not reflow it because I found no line-length config in the repository.

I did not use git and did not commit anything. The changes are uncommitted in the working tree.
