I changed `format_amount` in `billing/export.py` to return `f"{value:.2f}"`, so every amount is written with exactly two decimal places (12.5 becomes "12.50", 3 becomes "3.00"). That matches the importer's `^\d+\.\d{2}$` check.

I updated the docstring, which only said "formatted for the export file", to describe the two-decimal output. I also added a short comment saying why the format is fixed: the vendor's importer rejects the whole file otherwise and we can't change it, with a pointer to #212.

I haven't run it. Two things to know:
- The format spec is `.2f`, which rounds half-to-even on the binary float value (for example 2.675 gives "2.67"). If amounts can arrive as floats with more than two decimals, or you need strict rounding, store them as `Decimal`.
- A negative amount would come out as "-5.00", which the importer's regex would reject. I assumed invoice amounts are never negative. Credit notes would need a separate decision.
