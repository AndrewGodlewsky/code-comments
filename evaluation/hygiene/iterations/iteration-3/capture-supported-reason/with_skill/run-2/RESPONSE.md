DATA-412: `write_batch` in `pipeline/stage.py` now writes each batch sorted by customer_id.

What changed: `write_batch` cleans every row first, then sorts the cleaned rows by `customer_id` (the value actually written) before passing them to the sink. A comment beside the code states the loader's single-pass merge-join assumption, the silent skip of out-of-order rows, and that the fix lives here because the loader is in another repository.

Checked: a three-row sample with ids " 9 ", "10" and "2" was written as 10, 2, 9, with emails lower-cased. I did not run any other tests because none exist in this repository.

Things to confirm:
- The sort is plain string order, so "10" sorts before "2". If the warehouse loader compares customer_id as a number, or with a different collation, the order must match that, or the loader will still skip rows. Please confirm the loader's comparison rule for customer_id.
- The sort needs the whole batch in memory. If `rows` is a generator for very large batches, that changes memory use.
- Rows with equal customer_id keep their input order (Python's sort is stable). If the loader needs a particular tie-break, tell me.
