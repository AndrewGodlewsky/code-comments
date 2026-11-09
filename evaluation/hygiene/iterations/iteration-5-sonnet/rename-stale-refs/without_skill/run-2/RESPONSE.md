I renamed `compute_total` to `invoice_total` everywhere in the billing package. The test suite passes.

What changed:
- `billing/totals.py`: the function definition.
- `billing/invoice.py`: the import, the call, and a comment that mentioned it.
- `billing/discounts.py`: a docstring that mentioned it.
- `tests/test_totals.py`: the import and the call.
- `docs/billing.md`: the reference to `billing.totals.compute_total`.

I found no remaining `compute_total` references in the repository.

Two things to know:
- There is no tax module in this repository, so I couldn't check it for its own `compute_total`. If it lives elsewhere and imports `billing.totals.compute_total`, those imports will need updating.
- I did not keep a `compute_total` alias, so any outside caller using the old name will break.
