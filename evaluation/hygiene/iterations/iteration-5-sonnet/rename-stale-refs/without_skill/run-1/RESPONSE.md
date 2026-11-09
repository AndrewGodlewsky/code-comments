I renamed `compute_total` to `invoice_total` everywhere it appeared in the billing package. The test suite still passes (1 test).

Files changed:
- `billing/totals.py`: the function definition.
- `billing/invoice.py`: the import, the call, and a comment that mentioned it.
- `billing/discounts.py`: a docstring reference.
- `tests/test_totals.py`: the import and the call in the test.
- `docs/billing.md`: the doc reference, now `billing.totals.invoice_total`.

A search for `compute_total` now finds nothing in the repository.

This repository has no tax module, so I couldn't check the new tax module's `compute_total` for conflicts. Anything outside this repo that imports `billing.totals.compute_total` will need updating, and I left no alias behind. Tell me if you want a temporary alias for a transition period.

I haven't committed anything.
