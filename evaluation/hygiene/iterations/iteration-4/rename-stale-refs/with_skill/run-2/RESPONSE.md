I renamed `compute_total` to `invoice_total` everywhere it appeared in this repository. Every occurrence was in the billing package, its docs or its test, so no reference is left behind.

Changed files:
- `billing/totals.py`: the function definition.
- `billing/invoice.py`: the import, the call, and the comment that names the function.
- `billing/discounts.py`: a docstring that says to apply the discount before the total.
- `docs/billing.md`: the function's fully qualified name.
- `tests/test_totals.py`: the import and the call.

The rename is name-only. The rounding behaviour, the docstrings and the comments are otherwise unchanged, and none of them became false. The new name is the same length as the old one, so no line lengths change.

Checks:
- `grep` finds no remaining `compute_total` in the repository.
- `python -m unittest discover -s tests -t .` runs 1 test, and it passes.

Two things to check:
- The repository has no tax module, so I could not confirm the clash you described. If the tax module lives in another repository, nothing here changes it. If it is meant to be in this repository, it is not here.
- Nothing is committed. The changes are uncommitted in the working tree.
