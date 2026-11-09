DATA-412: staged batches are now written sorted by customer_id

What changed: `write_batch` in `pipeline/stage.py` now cleans every row first, then writes the batch sorted by the cleaned `customer_id`. The warehouse loader merge-joins in a single pass and silently skips out-of-order rows, so this keeps each batch in the order it needs.

Details:
- The sort runs after `clean()`, so the key is the id as it is actually written (the trimmed value). Sorting before trimming could put ids in the wrong order.
- The batch is materialised in memory before writing, because a sorted output needs every row first. If batches are very large, this is the first thing to revisit.
- I added a short docstring to `write_batch` explaining why the sort exists. No existing comment or docstring became false.

Checks: I ran a small smoke test with three rows (ids " 10 ", "2", "1") and the output order was "1", "10", "2". I did not run the warehouse loader or a full pipeline load, so the end-to-end fix is not yet confirmed.

Open point: the sort is plain Python string order. If the loader compares customer_id in a different order (for example, numerically, or with a different collation), the sort key must match it. Please confirm the loader's comparison rule before the next load.

Not done: no git operations, and nothing outside this repository directory was read or changed.
