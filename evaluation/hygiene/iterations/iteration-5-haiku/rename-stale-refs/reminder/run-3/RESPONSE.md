I renamed `compute_total` to `invoice_total` across the billing package. The rename covers the definition in `billing/totals.py`, the import and call in `billing/invoice.py`, the test in `tests/test_totals.py`, and the references in `billing/discounts.py` (docstring) and `docs/billing.md`.

Comments: the rename was the only change needed. The comment in `invoice.py` and the `discounts.py` docstring still describe the behaviour correctly under the new name, so I only updated the names in them. I also rewrapped two lines that grew past 79 characters (one test assertion, one line of `docs/billing.md`).

Verification: the unit test passes (`python -m unittest discover -s tests`). No `compute_total` references remain in the repository.

One thing to check: this repository has no tax module. The only other modules are `billing/discounts.py`, `billing/invoice.py`, and `billing/totals.py`. So nothing here collides with the new tax module's `compute_total`. If that module lives elsewhere, the clash will show up only when the two packages are used together, and this rename does not touch it.
