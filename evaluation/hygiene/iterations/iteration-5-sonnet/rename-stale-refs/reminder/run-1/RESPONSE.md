Renamed `compute_total` to `invoice_total` everywhere in the billing package: the definition in `billing/totals.py`, the import and call in `billing/invoice.py`, and the test in `tests/test_totals.py`.

The references in prose changed too, so they don't point at a name that no longer exists. These are the `apply_discount` docstring in `billing/discounts.py`, the comment in `billing/invoice.py`, and `docs/billing.md`. I added no new comments.

A search finds no remaining `compute_total`, and the tests pass.

I left one existing oddity alone. The comment in `invoice.py` says the total can differ "by a few pence", while the code rounds to the cent. It isn't affected by the rename, so I didn't touch it.
