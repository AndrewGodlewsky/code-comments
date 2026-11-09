I renamed `compute_total` to `invoice_total` across the billing package. The definition is in `billing/totals.py`, and the call sites are in `billing/invoice.py`, `billing/discounts.py` (a docstring), `docs/billing.md` and `tests/test_totals.py`. The docs and test were included because they reference the old name and would otherwise break.

The rename is a plain word-for-word substitution, and the existing comments and docstrings were still accurate afterwards, so I left their wording alone. The test suite passes (`python -m unittest discover -s tests -t .`, 1 test OK).

One thing to check: this repository has no tax module, so I could not confirm the clash you described. Nothing outside the billing package and its docs/tests was touched. If the tax module lives in another repository, nothing there needs to change for this rename.
