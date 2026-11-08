I renamed `compute_total` to `invoice_total` across the billing package. The changes are uncommitted.

Files changed:
- `billing/totals.py`: the function definition.
- `billing/invoice.py`: the import, the call in `render`, and the comment above it.
- `billing/discounts.py`: the docstring cross-reference in `apply_discount`.
- `tests/test_totals.py`: the import and the test call.
- `docs/billing.md`: the function reference.

No `compute_total` references remain in the repository. The unit test suite passes (1 test).

Two things to check:
- This repository has no tax module, so I could not confirm that the name is free of collisions with the new tax module's `compute_total`. Only the billing side was changed.
- Any caller outside this repository that imports `billing.totals.compute_total` will break until it is updated to `invoice_total`.

The comments that mentioned the function still describe its behaviour correctly after the rename, so I left their wording unchanged apart from the name.
