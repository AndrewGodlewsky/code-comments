I renamed `compute_total` to `invoice_total` everywhere in the billing package, and the one existing test still passes.

The rename touched:
- the definition in `billing/totals.py`
- the import and call in `billing/invoice.py`
- the test import and call in `tests/test_totals.py`

It also covered the places that only mention the name in text, so nothing refers to the old name any more:
- the `apply_discount` docstring in `billing/discounts.py`
- the comment above the total in `billing/invoice.py`
- `docs/billing.md`

I changed no behaviour and left every other comment as it was, since they were still accurate. I did not touch the new tax module, which was not in this repository, so its own `compute_total` is untouched.
