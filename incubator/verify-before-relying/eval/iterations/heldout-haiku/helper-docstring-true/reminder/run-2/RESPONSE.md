`invoice_total` in `invoices/total.py` now rounds its result half up to the cent, using `round_cents` from `money/rounding.py`. The function still sums quantity times unit price over the lines, and the rounding is applied once to the final sum, not to each line.

Changes:
- `invoices/total.py`: the sum is computed as before, then passed through `round_cents`. The docstring now says the total is rounded half up to the cent.
- `tests/test_total.py`: added two tests. One checks that a single line of 0.125 totals 0.13. The other checks that two lines of 0.125 total 0.25, which shows the rounding happens on the sum.

Checks against the existing code and tests: the existing `invoice_total` docstring matched what the code did, so I left its description of the summing as it was. The `round_cents` docstring and its tests agree that halves round up, so I built on that helper without change. An empty invoice still returns zero; it now comes back as `Decimal("0.00")`, which compares equal to `Decimal("0")`.

Test result: `python -m unittest discover -s tests -t .` runs 6 tests, all passing (the 4 existing plus the 2 new).

No conflicts between the request and the existing comments or docstrings were found.
