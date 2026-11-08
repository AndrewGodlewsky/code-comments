I renamed `compute_total` to `invoice_total` throughout the billing package. The definition is in `billing/totals.py`, and its callers are updated in `billing/invoice.py`.

Two files outside the package also referenced the function, so I updated them too. Leaving them alone would have broken the test import and pointed the docs at a name that no longer exists:
- `tests/test_totals.py` imports and calls the renamed function.
- `docs/billing.md` names `billing.totals.compute_total`.

A docstring in `billing/discounts.py` and a comment in `billing/invoice.py` also mentioned the old name, and I updated both. Their wording was otherwise still accurate, so nothing else changed.

The test suite passes (`python -m unittest`, 1 test). No `compute_total` references remain in the directory. I did not touch git.

There is no tax module in this directory, so I could not check the clash you mentioned. The old name is now free in this package, but if the tax module lives elsewhere and imports `billing.totals.compute_total`, it will need the same update.
