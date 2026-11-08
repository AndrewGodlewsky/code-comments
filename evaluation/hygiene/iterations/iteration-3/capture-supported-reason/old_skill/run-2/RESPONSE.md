DATA-412: staging batches are now written sorted by customer_id

I changed `write_batch` in `pipeline/stage.py` so each batch is cleaned, sorted by the cleaned `customer_id`, and then written. The loader merge-joins on customer_id in a single pass and silently skips out-of-order rows, so this ordering is what prevents the drop. The loader itself is untouched.

What changed:
- `write_batch` now materializes the batch, sorts it on the cleaned `customer_id` (the value that is written, after `strip()`), and writes the rows in that order.
- A comment at the point of the sort records the loader's single-pass merge-join and the silent skip, so the next editor does not remove the sort.

Checks:
- A quick smoke run on three sample rows, including one with surrounding whitespace in the id, wrote them as `1`, `10`, `2`, with each row's email still lower-cased.
- I did not run the loader or the full pipeline, and I did not add a test file.

Things to be aware of:
- Ordering uses Python's default string comparison. If the warehouse loader sorts customer_id differently (for example numerically, or with a different collation), the batches could still be skipped. Please confirm the loader's ordering rule.
- Sorting needs the whole batch in memory before the first write. If batches are large, this is a memory cost to check.
- The 3% already missing from last night's load will not be recovered by this change. The affected rows need to be reloaded, for example by re-running the batches through the fixed code.
