Renamed `compute_total` to `invoice_total` everywhere in the billing package: the definition in `billing/totals.py`, the import and call in `billing/invoice.py`, and the test in `tests/test_totals.py`.

References in prose were updated too, so nothing points at the old name: the `apply_discount` docstring in `billing/discounts.py`, the comment in `billing/invoice.py`, and `docs/billing.md`. The wording of those comments was still accurate, so only the name changed. I added no new comments.

A search finds no remaining `compute_total`. The tests pass. I did not touch the new tax module, which was not in this repository.
