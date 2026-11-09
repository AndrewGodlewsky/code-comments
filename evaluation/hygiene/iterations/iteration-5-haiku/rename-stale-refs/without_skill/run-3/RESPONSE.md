I renamed `compute_total` to `invoice_total` across the billing package. No `compute_total` references remain in the repo.

Changed files:
- `billing/totals.py`: the function definition.
- `billing/invoice.py`: the import, the call, and the comment.
- `billing/discounts.py`: the docstring reference.
- `docs/billing.md`: the function path and description.
- `tests/test_totals.py`: the import and the call.

The one test (`TotalsTest.test_rounds_each_line_before_adding`) passes after the rename.

One thing to check: this repo has no tax module, so I could not see the `compute_total` you mentioned there. I did not touch anything outside the billing package, its docs and its tests. If the tax module lives in another repo, its `compute_total` is unaffected by this change. If it lives in this repo under a path I did not find, tell me and I will look again.

I did not commit anything.
