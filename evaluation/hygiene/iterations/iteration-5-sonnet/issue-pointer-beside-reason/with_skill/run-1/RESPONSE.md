I changed `format_amount` in `billing/export.py` to return `f"{value:.2f}"`, so 12.5 becomes "12.50" and 3 becomes "3.00". I did not run it or add tests.

I added a note to the `format_amount` docstring. It says the vendor's importer rejects the whole file if any amount doesn't match `^\d+\.\d{2}$`, that we can't change the importer, and that this is tracked in #212.

- **Negatives:** the regex has no sign, so a negative amount (a credit note, say) would still fail the import. I didn't handle this because nothing in the request says whether negatives occur or how the vendor wants them written. Can you tell me?
- **Rounding:** `:.2f` rounds values with more than two decimals (floats use round-half-even on the binary value). If amounts can be `Decimal` or have sub-cent precision, tell me the intended rounding rule.
