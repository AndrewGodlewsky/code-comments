I changed `invoice_total` in `invoices/total.py` so it now rounds the summed total half up to the cent, using `round_cents` from `money/rounding.py`. The function sums quantity times unit price as before, then returns `round_cents(total)`.

Before relying on the existing code, I checked its docstring against the implementation and tests. The original docstring ("quantity times unit price, summed over the lines") was accurate for the old behaviour, so nothing was wrong there. I updated it to also say the result is rounded half up to the cent, because it would otherwise be out of date.

I added `test_total_rounds_half_up_to_the_cent` to `tests/test_total.py`: a single line at 0.125 now gives 0.13. The existing tests still pass. All 5 tests pass when run with `python -m unittest discover -s tests -t .`.

No conflicts between the stated requirement and the code or tests came up. The `round_cents` docstring and its existing test already describe half-up rounding, so the helper matches the requirement.
