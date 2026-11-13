DATA-412: `write_batch` in `pipeline/stage.py` now writes each batch sorted by `customer_id`.

What changed: `write_batch` cleans every row first, then sorts the batch by the cleaned `customer_id` before writing. Sorting after `clean()` matters because `clean()` trims the id, so sorting on the raw value could order rows differently from the loader's view. I added a comment above the loop stating why the sort exists (the loader's single-pass merge-join silently skips out-of-order rows, DATA-412). `pipeline/__init__.py` was empty and is unchanged.

Points to check:
- Sort order is Python's default string ordering. If the warehouse loader expects a different collation (for example numeric ids, or a specific database collation), the sort needs to match it. The ticket does not say which, so please confirm.
- The sort is stable, so duplicate `customer_id` rows keep their input order. I did not confirm whether the loader handles duplicates.
- Sorting needs the whole batch in memory before writing, where the old code streamed row by row. Fine for normal batch sizes; worth knowing if batches can be very large.
- I smoke-tested the ordering with a three-row sample (output `['a', 'b', 'c']`). There is no test suite in this directory, so no tests were added or run.
