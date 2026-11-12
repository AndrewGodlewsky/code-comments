I changed `write_batch` in `pipeline/stage.py` so each batch is cleaned, sorted by the cleaned `customer_id`, and then written. The loader merge-joins on `customer_id` in one pass and silently skips out-of-order rows, so this sort is the fix on our side. I added a docstring to `write_batch` recording that constraint and ticket DATA-412. `clean` and the module docstring were already accurate and are unchanged. `pipeline/__init__.py` is empty and was not changed.

Two things you should check:

1. Sort order. I sorted with Python's default string comparison. If the loader compares `customer_id` as numbers, or with a different collation, string order would still be out of order for ids such as "9" and "10". I could not verify the loader's comparison rule from this repository, so please confirm it. If it is numeric, the sort key needs to change.
2. Materialised batch. `write_batch` now reads the whole input into memory before writing. This is needed to sort, but it matters if batches can be very large.

I did not run any tests, because the repository has none in the provided inputs.
