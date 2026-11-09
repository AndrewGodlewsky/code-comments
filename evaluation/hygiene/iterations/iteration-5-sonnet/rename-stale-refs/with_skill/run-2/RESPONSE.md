I renamed `compute_total` to `invoice_total` everywhere in the billing package, and the one existing test passes.

What changed:
- `billing/totals.py`: the definition.
- `billing/invoice.py`: the import, the call, and the comment that named the function.
- `billing/discounts.py`: the `apply_discount` docstring that said to apply it before `compute_total`.
- `tests/test_totals.py`: the import and the call.
- `docs/billing.md`: the reference to `billing.totals.invoice_total`.

No `compute_total` references remain. The comments and docstrings only needed the new name, so I added no new comments.

Two things to check:
- I did not touch the new tax module, since it is not in this repository. Its own `compute_total` is unaffected. Any code outside this repository that imports `billing.totals.compute_total` will break.
- `invoice.py` has a comment saying the printed total can differ from the unrounded sum by "a few pence". The code rounds to the cent. I left that wording alone because the rename did not cause it, but you may want to fix the currency unit.
